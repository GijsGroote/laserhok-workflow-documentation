import glob
import os
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from global_variables import gv
from src.worker import Worker

from laser_job_tracker import LaserJobTracker
from src.button import JobsQPushButton
from src.directory_functions import open_folder
from src.loading_dialog import LoadingQDialog
from src.directory_functions import delete

from convert import split_material_name
from src.mail_manager import MailManager
from src.qdialog import SelectOptionsQDialog


from src.directory_functions import copy_item
from src.qmessagebox import TimedMessage, JobFinishedMessageBox, YesOrNoMessageBox, ErrorQMessageBox, WarningQMessageBox
from laser_qlist_widget import MaterialContentQListWidget
from requests.exceptions import ConnectionError


class LaserKlaarQPushButton(JobsQPushButton):

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.threadpool = gv["THREAD_POOL"]
        self.clicked.connect(self.on_click)
 
    def on_click(self):
        job_name = self.getCurrentItemName()
        
        job_folder_global_path = LaserJobTracker(self).getJobFolderGlobalPathFromJobName(job_name)
        self.threadedSendFinishedMail(job_folder_global_path)

        LaserJobTracker(self).updateJobStatus(job_name, 'VERWERKT')
        self.refreshAllQListWidgets()

    def threadedSendFinishedMail(self, job_folder_global_path):
        ''' Send job finished mail on an other thread. '''

        if not any([file.endswith(('.msg', '.eml')) for file in os.listdir(job_folder_global_path)]):
            WarningQMessageBox(gv=gv, parent=self, text=f'No Job finished mail send because: No mail file found')
            return

        send_mail_worker = Worker(self.sendFinishedMail, gv=gv, job_folder_global_path=job_folder_global_path)
        send_mail_worker.signals.result.connect(self.finishedMailSendMessage)
        send_mail_worker.signals.error.connect(self.handleMailError)
        self.threadpool.start(send_mail_worker)

    def sendFinishedMail(self, gv: dict, job_folder_global_path: str):
        ''' Send a job finished mail. '''

        mail_manager = MailManager(gv)
        mail_manager.replyToEmailFromFileUsingTemplate(
                mail_manager.getMailGlobalPathFromFolder(job_folder_global_path),
                'FINISHED_MAIL_TEMPLATE',
                {},
                popup_reply=False)
        
        return self.getCurrentItemName()   

    def finishedMailSendMessage(self, data):
        ''' Display a message with: finished mail send. '''
        TimedMessage(gv, parent=self, text=f'Confimation mail send to {data}')

    def handleMailError(self, exc: Exception):
        ''' Handle mail error. '''

        assert isinstance(exc, Exception), f'Expected type Exception, received type: {type(exc)}'

        if isinstance(exc, ConnectionError):
            ErrorQMessageBox(self,
                    text=f'Connection Error, No Job Finished mail send:\n{str(exc)}')
        else:
            ErrorQMessageBox(self, text=f'Error Occured, No Job Finished mail send:\n{str(exc)}')


class MateriaalKlaarQPushButton(JobsQPushButton):

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.clicked.connect(self.on_click)

        self.threadpool = gv['THREAD_POOL']

 
    def on_click(self):
        material_name = self.getCurrentItemName()
        material, thickness = split_material_name(material_name)

        job_tracker = LaserJobTracker(self)

        # todo: not all is always done
        dxfs_names_and_global_paths = job_tracker.getDXFsAndPaths(material, thickness)

        dialog = SelectOptionsQDialog(self, dxfs_names_and_global_paths)

        if dialog.exec_() == QDialog.Accepted:

            files_names = []
            files_global_paths = []
            for item in dialog.optionsQListWidget.selectedItems():
                files_names.append(item.text())
                files_global_paths.append(item.data(1))
        else:
            return

        for file_global_path in files_global_paths:
            # find job_name
            job_name = job_tracker.fileGlobalPathToJobName(file_global_path)

            # material done, mark it done
            job_tracker.markFileIsDone(job_name, file_global_path)

            # if all is done, display message
            if job_tracker.isJobDone(job_name):
                # hey this material is done!

                TimedMessage(gv, self, f"Job finished mail send to {job_name}")

                job_tracker.updateJobStatus(job_name, 'VERWERKT')
                job_folder_global_path = job_tracker.getJobFolderGlobalPathFromJobName(job_name)

                try:
                    self.sendFinishedMail(gv, job_name, job_folder_global_path)
                except ConnectionError as e:
                    TimedMessage(self, text=str(e))
                    return

                JobFinishedMessageBox(text=f"Job {job_name} is finished, put it the Uitgifterek:\n"\
                        f"{job_tracker.getLaserFilesString(job_name)}",
                            parent=self)

        self.refreshAllQListWidgets()


class AfgekeurdQPushButton(JobsQPushButton):

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.clicked.connect(self.on_click)
        self.threadpool = gv['THREAD_POOL']

    def on_click(self):
        job_name = self.getCurrentItemName()
        job_tracker = LaserJobTracker(self)
        job_tracker.updateJobStatus(job_name, 'AFGEKEURD')
        self.refreshAllQListWidgets()

        job_folder_global_path = job_tracker.getJobFolderGlobalPathFromJobName(job_name)

        self.threadedSendDeclineMail(job_name, job_folder_global_path)
        
    def threadedSendDeclineMail(self, job_name, job_folder_global_path):
        ''' Send decline mail on an other thread. '''

        # TODO: dear lord write a function to find the top level parent
        self.loading_dialog = LoadingQDialog(self.parent().parent().parent().parent().parent().parent(), gv, text='Send the Outlook popup reply, it can be behind other windows')
        self.loading_dialog.show()
     
        send_mail_worker = Worker(self.sendDeclinedMail, gv=gv, job_folder_global_path=job_folder_global_path)
        send_mail_worker.signals.finished.connect(self.loading_dialog.accept)
        send_mail_worker.signals.error.connect(self.loading_dialog.accept)
        send_mail_worker.signals.error.connect(self.handleMailError)
        self.threadpool.start(send_mail_worker)

    def sendDeclinedMail(self, gv: dict, job_folder_global_path: str):
        ''' popup the Declined mail. '''
        mail_manager = MailManager(gv)
        mail_manager.replyToEmailFromFileUsingTemplate(
                mail_manager.getMailGlobalPathFromFolder(job_folder_global_path),
                'DECLINED_MAIL_TEMPLATE',
                {},
                popup_reply=True)
        
    def handleMailError(self, exc):
        ''' Handle mail error. '''

        assert isinstance(exc, Exception), f'Expected type Exception, received type: {type(exc)}'

        if isinstance(exc, ConnectionError):
            ErrorQMessageBox(self,
                    text=f'Connection Error, No Job Declined mail send:\n{str(exc)}')
        else:
            ErrorQMessageBox(self, text=f'Error Occured, No Job Declined mail send:\n{str(exc)}')


class OptionsQPushButton(JobsQPushButton):

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.menu = QMenu()

        self.object_name = self.objectName()
        self.menu.addAction('Open in File Explorer', self.openInFileExplorer)
        self.menu.addAction('Delete Job', self.deleteJob)

        # initialize  
        self.objectNameChanged.connect(self.storeObjectNameInit)

    def storeObjectNameInit(self):
        ''' store the object name and initialize. '''
        self.object_name = self.objectName()

        if self.object_name == 'allJobsOptionsQPushButton':
            self.menu.addAction('Move to Wachtrij', self.moveJobToWachtrij)
                        
        elif self.object_name == 'wachtrijOptionsQPushButton':
            self.menu.addAction('Copy Files to ..', self.copyLaserFilesTo)

        elif self.object_name == 'wachtrijMateriaalOptionsQPushButton':
            self.menu.addAction('Copy Files to ..', self.copyMaterialWachtrijFilesTo)

        elif self.object_name == 'verwerktOptionsQPushButton':
            self.menu.addAction('Copy Laser Files to ..', self.copyLaserFilesTo)
            self.menu.addAction('Move to Wachtrij', self.moveJobToWachtrij)
            self.menu.addAction('Move to Afgekeurd', self.moveJobToAfgekeurd)

        elif self.object_name == 'afgekeurdOptionsQPushButton':
            self.menu.addAction('Copy Laser Files to ..', self.copyLaserFilesTo)
            self.menu.addAction('Move to Wachtrij', self.moveJobToWachtrij)
            self.menu.addAction('Move to Verwerkt', self.moveJobToVerwerkt)

        else:
            raise ValueError(f'could not identify {self.object_name}')

        self.setMenu(self.menu)

    def moveJobToWachtrij(self):
        self.moveJobTo('WACHTRIJ')

    def moveJobToAfgekeurd(self):
        self.moveJobTo('AFGEKEURD')

    def moveJobToVerwerkt(self):
        self.moveJobTo('VERWERKT')

    def moveJobTo(self, new_status):
        job_name = self.getCurrentItemName()
        LaserJobTracker(self).updateJobStatus(job_name, new_status)
        self.refreshAllQListWidgets()

    def openInFileExplorer(self):
        job_folder_global_path = self.getJobFolderGlobalPath()
        open_folder(job_folder_global_path)

    def deleteJob(self):
        job_name = self.getCurrentItemName()
        LaserJobTracker(self).deleteJob(job_name)
        self.refreshAllQListWidgets()

    def getJobFolderGlobalPath(self):
        job_name = self.getCurrentItemName()
        return LaserJobTracker(self).getJobDict(job_name)['job_folder_global_path']
    
    def copyLaserFilesTo(self):
        '''Copy the laser files from a job to a specified folder. '''

        job_name = self.getCurrentItemName()
        laser_file_dict =  LaserJobTracker(self).getLaserFilesDict(job_name)
        target_folder_global_path = gv['LASER_TODO_DIR_HOME']

        # clear the laser todo dir home first
        for file in os.listdir(target_folder_global_path):
            delete(os.path.join(target_folder_global_path, file))
                   
        for file_key, file_dict in laser_file_dict.items():

            # TODO: you could copy all unwanted stuff better
            source_item_global_path = file_dict['file_global_path']
            target_item_global_path = os.path.join(target_folder_global_path,
                file_dict['material']+"_"+file_dict['thickness']+'mm_'+file_dict['amount']+"x_"+file_key)

            copy_item(source_item_global_path, target_item_global_path)

        open_folder(target_folder_global_path)

    def copyMaterialWachtrijFilesTo(self):
        ''' Copy the dxf files in wachtrij to a specified folder. '''

        material_name = self.getCurrentItemName()
        

        material, thickness = split_material_name(material_name)

        dxfs_names_and_global_paths = LaserJobTracker(self).getDXFsAndPaths(material, thickness)

        target_folder_global_path = gv['LASER_TODO_DIR_HOME']

        # clear the laser todo dir home first
        for file in os.listdir(target_folder_global_path):
            print( f'delet file {os.path.join(target_folder_global_path, file)}')
            delete(os.path.join(target_folder_global_path, file))

        for file_name, file_global_path in dxfs_names_and_global_paths:
            copy(file_global_path, os.path.join(target_folder_global_path, file_name))

        open_folder(target_folder_global_path)