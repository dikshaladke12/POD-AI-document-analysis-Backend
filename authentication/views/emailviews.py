
from django.shortcuts import render
from ..models import *

def varification_mail(request):
    email = EmailTemplate.objects.first()
    
    context = {'email': email.html_body, 'first_name':'Ankush'}  # pass email template details to template
    return render(request, 'Email-Template/email.html', context)
