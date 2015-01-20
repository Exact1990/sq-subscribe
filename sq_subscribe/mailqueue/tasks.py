# -*- coding: utf-8 -*-
from celery.task import task
from django.core import mail
from sq_subscribe.mailqueue.models import MailQueue, create_mailqueue


@task(name='send_concrete_mailqueue',ignore_result=True)
def send_concrete_mailqueue(queue_ids):
    if len(queue_ids) > 0:
        connection = None
        try:
            connection = mail.get_connection(fail_silently=True)
            connection.open()
            for email_id in queue_ids:
                try:
                    email = MailQueue.objects.get(pk=email_id)
                    connection = mail.get_connection()
                    organization = email.organization
                    if organization.exists_settings_email():
                        connection.password = organization.email_host_password
                        connection.username = organization.email_host_user
                        connection.host = organization.email_host
                        connection.port = organization.email_port
                        connection.use_tls = organization.email_use_tls
                    msg = email.send_email(connection)
                    msg.send()
                except Exception:
                    print 'MESSAGE %s CAN NOT SENDED'%email.id
        finally:
            if connection:
                connection.close()


#Асинхронная отправка сообщения, подойдет для уведомлений.
@task(name='send_email_message')
def send_email_message(subject,template,send_to,content_type,message=None,send_from=None):
    email = create_mailqueue(subject,template,send_to,content_type,message,)
    connection = None
    try:
        connection = mail.get_connection(fail_silently=True)
        connection.open()
        msg = email.send_email(connection)
        try:
            msg.send()
            email.delete()
        except Exception:
            raise('MESSAGE %s CAN NOT SENDED'%email.id)
    finally:
        connection.close()