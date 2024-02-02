from PyQt5 import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from src.qmessagebox import InfoQMessageBox, WarningQMessageBox, ErrorQMessageBox, TimedMessage
from src.worker import Worker, WorkerSignals
from src.mail_manager import MailManager


class ThreadedMailManager():
    ''' 
    Worker specific for threaded mail operations such 
    as sending mail, retrieving mail, or moving mail to a seperate folder. 
    '''

    def __init__(self, parent_widget, gv:dict):
        self.gv=gv
        self.thread_pool = gv['THREAD_POOL']
        self.parent_widget = parent_widget
        self.worker = None
    
    def startReceivedMailWorker(self,
                            success_message: str,
                            error_message: str,
                            job_folder_global_path: str,
                            template_content: dict,
                            msg):
        
        self.success_message = success_message
        self.error_message = error_message
        self.msg = msg

        self.worker = Worker(self.sendReceivedMail,
                             job_folder_global_path=job_folder_global_path,
                             template_content=template_content)

        self.worker.signals.finished.connect(self.displaySuccessMessage)
        self.worker.signals.error.connect(self.handleMailError)

        self.thread_pool.start(self.worker)


    def sendReceivedMail(self,
                                job_folder_global_path: str,
                                template_content: dict):
        """ Send a confirmation mail. """

        # The MailManager object must be made in the scope of this function. 
        # otherwise Outlook raises an attribute error for an open share com object
        mail_manager = MailManager(self.gv)
        

        mail_manager.replyToEmailFromFileUsingTemplate(
                                msg_file_path=mail_manager.getMailGlobalPathFromFolder(job_folder_global_path),
                                template_file_name="RECEIVED_MAIL_TEMPLATE",
                                template_content=template_content,
                                popup_reply=False)

        mail_manager.moveEmailToVerwerktFolder(msg=self.msg)
    
    def startFinishedMailWorker(self,
                            success_message: str,
                            error_message: str,
                            job_folder_global_path: str,
                            template_content: dict):        
        self.success_message = success_message
        self.error_message = error_message

        self.worker = Worker(self.sendFinishedMail,
                             job_folder_global_path=job_folder_global_path,
                             template_content=template_content)

        self.worker.signals.finished.connect(self.displaySuccessMessage)
        self.worker.signals.error.connect(self.handleMailError)
        self.thread_pool.start(self.worker)

    def sendFinishedMail(self,
                        job_folder_global_path: str,
                        template_content: dict):
        """ Send a confirmation mail. """
        
        # The MailManager object must be made in the scope of this function. 
        # otherwise Outlook raises an attribute error for an open share com object
        mail_manager = MailManager(self.gv)

        mail_manager.replyToEmailFromFileUsingTemplate(
                                msg_file_path=mail_manager.getMailGlobalPathFromFolder(job_folder_global_path),
                                template_file_name="FINISHED_MAIL_TEMPLATE",
                                template_content=template_content,
                                popup_reply=False)

    def displaySuccessMessage(self):
        ''' Display a confirmation message to the user. '''
        TimedMessage(self.gv, parent=self.parent_widget, text=self.success_message)

    def handleMailError(self, exc: Exception):
        ''' Handle the mail Error. '''
        assert isinstance(exc, Exception), f'Expected type Exception, received type: {type(exc)}'

        if isinstance(exc, ConnectionError):
            ErrorQMessageBox(self.parent_widget, text=f'Connection Error {self.error_message}: {str(exc)}')
        else:
            ErrorQMessageBox(self.parent_widget, text=f'Error Occured: {str(exc)}')

