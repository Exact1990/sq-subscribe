# -*- coding: utf-8 -*-
from datetime import datetime
from django.contrib.sites.models import Site
from django.template.base import TemplateDoesNotExist, TemplateSyntaxError
from django.template.context import Context
from django.utils import simplejson as json

from django.core.mail.message import EmailMultiAlternatives, EmailMessage
from django.db import models
from django.template.loader import render_to_string, get_template_from_string
from django.utils.html import strip_tags
from django.conf import settings
from apps.main.utils import ATTACHMENT_PATH
from apps.organization.models import Organization
import os


CONTENT_TYPE = [
    ('plain', u'В текстовом формате'),
    ('html', u'В формате HTML'),
]

class MailQueue(models.Model):
    send_to = models.CharField(max_length=1000,null=False)
    send_from = models.EmailField(null=False)
    subject = models.CharField(max_length=1000,null=True,blank=True,default=u'Без темы')
    message = models.TextField()
    template = models.TextField(blank=True)
    created_date = models.DateTimeField(default=datetime.now())
    content_type = models.CharField(max_length=100, blank=True, choices=CONTENT_TYPE)
    organization = models.ForeignKey(Organization,verbose_name=u'Сообщество', null=True, blank=True)


    def __unicode__(self):
        return u'Mail message %s' % self.subject

    class Meta:
        db_table = 'mailqueue'
        verbose_name = 'Письмо'
        verbose_name_plural = 'Письма'


    def send_email(self,connecion):
        vars = json.loads(self.message)
        template_directory =  getattr(settings, "EMAIL_TEMPLATE_DIR", 'email')
        if self.template.endswith('.html') or self.template.endswith('.txt'):
            try:
                html_content = render_to_string(template_directory+'/%s'%self.template,vars)
            except TemplateDoesNotExist:
                raise TemplateDoesNotExist('Template dir %s does not exist.'%template_directory)
            text_content = strip_tags(html_content)
        else:
            try:
                t = get_template_from_string(self.template)
                html_content = t.render(Context(vars))
            except TemplateSyntaxError:
                raise TemplateSyntaxError('Template syntax error.')
            text_content = strip_tags(html_content)
        try:
            if self.content_type == 'html':
                send_to_list = self.send_to.split(",")
                if len(send_to_list)>0:
                    msg = EmailMultiAlternatives(self.subject,text_content,from_email=self.send_from,to=[send_to_list[0]],connection=connecion, bcc=send_to_list[1:], headers={'Cc': ','.join(send_to_list[1:])})
                else:
                    msg = EmailMultiAlternatives(self.subject,text_content,from_email=self.send_from,to=[send_to_list[0]],connection=connecion)
                msg.attach_alternative(html_content,"text/html")
            else:
                send_to_list = self.send_to.split(",")
                
                if len(send_to_list)>0:
                    msg = EmailMessage(self.subject,text_content,from_email=self.send_from,to=[send_to_list[0]],connection=connecion, bcc=send_to_list[1:], headers={'Cc': ','.join(send_to_list[1:])})
                else:
                    msg = EmailMessage(self.subject,text_content,from_email=self.send_from,to=[send_to_list[0]],connection=connecion)
            if ('attachment' in vars['data']) and (vars['data']['attachment']!={}):
                path = vars['data']['attachment']['att_file_path']
                with open(path, 'r') as f:
                    msg.attach(vars['data']['attachment']['att_file_name'], f.read(), vars['data']['attachment']['att_file_type'])
                f.closed
                os.remove(path)
        except Exception:
            raise Exception('Email message %s can not created.'%self.id)
        self.delete()
        return msg

def create_mailqueue(subject, template, send_to, content_type, message=None, send_from=None, attachment=None, organization=None):
    if not message: message = {}
    if not attachment: attachment = {}
    if organization.exists_settings_email():
        send_from = organization.email_from
    if send_from is None:
        from django.conf import settings
        send_from = settings.DEFAULT_FROM_EMAIL
    #site = Site.objects.get_current()

    message.update({"site":{'name': organization.name,'domain':organization.domain, 'email_manager': organization.email_manager},"attachment":attachment})
    msg = {"data":message}
    mail = MailQueue.objects.create(message=json.dumps(msg),send_to=send_to,subject=subject,template=template,send_from=send_from,content_type=content_type, organization=organization)
    mail.save()
    return mail


def send_email(subject,template,send_to,content_type, message=None,send_from=None,attachment=None, organization=None):
    from django.conf import settings
    from apps.user.models import User
    try:
        user = User.objects.get(email=send_to)
        if user.organization is not None:
            organization = user.organization
    except:
        user = None
    if organization is not None:
        import datetime
        import pytz
        datestart = datetime.datetime(year=2013, month=12, day=2, hour=0, minute=0, second=0, microsecond=0, tzinfo=pytz.utc)
        if not settings.DEBUG or user is None or (settings.DEBUG and (user.is_staff or user.date_joined > datestart)):
            attach_t = {}
            if attachment is not None:
                att_file_path = ATTACHMENT_PATH + u'/' + attachment['att_file_name']
                with open(att_file_path, 'w') as f:
                    f.write(attachment['att_file'])
                    f.closed
                    attach_t.update({'att_file_name': attachment['att_file_name'], 'att_file_path': att_file_path, 'att_file_type': attachment['att_file_type']})

            from sq_subscribe.mailqueue.tasks import send_concrete_mailqueue
            mail = create_mailqueue(subject,template,send_to,content_type,message,send_from,attach_t, organization)
            #TODO нужно придумать, как сделать проверку - отправлять ли письмо по таску или мгновенно.
            send_concrete_mailqueue.delay([mail.id])