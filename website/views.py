# -*- coding: utf-8 -*-
from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.files.uploadedfile import UploadedFile
from django.db.models.query_utils import Q
from django.db.utils import IntegrityError
from django.utils import simplejson as json
from django.forms.models import ModelForm, ModelChoiceField
from django.shortcuts import render_to_response, get_object_or_404
from django.template.context import RequestContext
from django import http
#from personel.models import Personel, Ileti
#from urun.models import Urun
from django.utils.encoding import force_unicode
from django.views.decorators.csrf import csrf_exempt
from places.countries import OFFICIAL_COUNTRIES_DICT, COUNTRIES_DICT
from places.models import Place, Tag, Photo, Currency, Profile
from django.db import DatabaseError
from places.options import n_tuple, PLACE_TYPES, SPACE_TYPES, JSTRANS, DJSTRANS
from utils.cache import kes
from utils.htmlmail import send_html_mail
from utils.kabuk import sonarzu
from website.models import Sayfa, Haber, Vitrin, Question
from django.contrib.sites.models import get_current_site
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from website.models.medya import Medya
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from  django.core.urlresolvers import reverse
from easy_thumbnails.files import get_thumbnailer
from django.contrib import auth
from django.contrib import messages
import logging
log = logging.getLogger('genel')
noOfBeds=n_tuple(7)
placeTypes = [(0,_(u'All'))] + PLACE_TYPES
from datetime import datetime
from paypal.pro.views import PayPalPro
from paypal.standard.forms import PayPalPaymentsForm

class SearchForm(forms.Form):
    checkin = forms.DateField(widget=forms.TextInput(attrs={'class':'vDateField'}),required=False)
    checkout = forms.DateField(widget=forms.TextInput(attrs={'class':'vDateField'}),required=False)
    query = forms.CharField(widget=forms.TextInput(), label=_(u'City or address'),required=False)
    no_of_guests = forms.ChoiceField(choices=noOfBeds, initial=1, label=_(u'Guests'),required=False)
    placeType = forms.ChoiceField(choices=placeTypes,required=False)

class BookingForm(forms.Form):
    checkin = forms.DateField(widget=forms.TextInput(attrs={'class':'vDateField'}))
    checkout = forms.DateField(widget=forms.TextInput(attrs={'class':'vDateField'}))
    no_of_guests = forms.ChoiceField(choices=noOfBeds, initial=1)


def showPlace(request, id):
    place = Place.objects.select_related().get(pk=id)
    owner = place.owner
    profile = owner.profile
    properties=(
        (_(u'Place type'),place.get_type_display()),
        (_(u'Space offered'),place.get_space_display()),
        (_(u'Accommodates'),place.capacity),
        (_(u'Size'), place.get_size()  ),
        (_(u'Bedrooms'),place.bedroom),
        (_(u'Bed type'),place.get_bed_type_display()),
        (_(u'Bathrooms'),place.bathrooms),
        (_(u'Cancellation'),place.get_cancellation_display()),
    )
    context = {'place':place,'bform':BookingForm(),'properties':properties , 'owner':owner, 'profile':profile, 'amens':place.getTags(request.LANGUAGE_CODE)}
    return render_to_response('show_place.html', context, context_instance=RequestContext(request))

def searchPlace(request):
    context = {}
    return render_to_response('search_place.html', context, context_instance=RequestContext(request))

class LoginForm(forms.Form):
    login_email = forms.EmailField(label=_(u'E-mail address'))
    login_pass = forms.CharField(widget=forms.PasswordInput(),label=_(u'Password'))

class RegisterForm(ModelForm):
    pass1 = forms.CharField(widget=forms.PasswordInput(),label=_(u'Password'))
    pass2 = forms.CharField(widget=forms.PasswordInput(),label=_(u'Password (Again)'))
    email = forms.EmailField(label=_(u'E-mail address'))
    class Meta:
        model=User
        fields = ('email','first_name','last_name',)

def anasayfa(request):
    sayfa = Sayfa.al_anasayfa()
    lang = request.LANGUAGE_CODE
    searchForm = SearchForm()
    context = {'slides': Vitrin.get_slides(), 'slides2': Vitrin.get_slides(type=1),
               'slides3': Vitrin.get_slides(type=2), 'srForm':searchForm }
    return render_to_response('index.html', context, context_instance=RequestContext(request))

class addPlaceForm(ModelForm):
    lat= forms.FloatField(widget=forms.HiddenInput())
    lon= forms.FloatField(widget=forms.HiddenInput())
    currency = ModelChoiceField(Currency.objects.filter(active=True), empty_label=None)

#    neighborhood= forms.FloatField(widget=forms.HiddenInput())

#    postcode= forms.CharField(widget=forms.HiddenInput())
    def __init__(self, *args, **kwargs):
        super(addPlaceForm, self).__init__(*args, **kwargs)
        self.fields['tags'].widget = forms.CheckboxSelectMultiple()
        self.fields["tags"].queryset = Tag.objects.all()
#        self.fields['currency'].queryset = Currency.objects.filter(active=True)

    class Meta:
        model=Place
        fields = ('title','type','capacity','space','description','price','currency',
            'city','country','district','street','address','lat','lon','neighborhood','state',
            'postcode','tags', 'min_stay', 'max_stay', 'cancellation','manual','rules','size','size', 'size_type'
            )

from appsettings import app
ghs = app.settings.gh

@login_required
def addPlace(request, ajax=False, id=None):
    template_name = "add_place_wizard.html" if ajax else "add_place.html"
    sayfa = Sayfa.al_anasayfa()
    lang = request.LANGUAGE_CODE
    user = request.user
    response = {}
    new_place = None
    loged_in = user.is_authenticated()
    photos = []
    if id:
        old_place = get_object_or_404(Place, pk=id)
        photos = old_place.photo_set.values_list('id',flat=True)
        if old_place.owner != request.user:
            return HttpResponseForbidden()
    else:
        old_place = Place()
    if request.method == 'POST':
        register_form = RegisterForm(request.POST)
        login_form = LoginForm(request.POST)
        form = addPlaceForm(request.POST, instance=old_place)
        if form.is_valid():
            new_place=form.save(commit=False)
            if register_form.is_valid() or loged_in:
                if not loged_in:
                    user = register_form.save(commit=False)
                    user.username = user.email
                    user.set_password(register_form.cleaned_data['pass1'])
                    user.save()
                new_place.owner = user
                new_place.lat = str(new_place.lat)
                new_place.lon = str(new_place.lon)
                new_place.save()
                form.save_m2m()
                for tag in form.cleaned_data['tags']:
                    new_place.tags.add(tag)
                new_place.save()
                tmp_photos = request.session.get('tmp_photos')
                if tmp_photos:
                    Photo.objects.filter(id__in=tmp_photos).update(place=new_place)
                    Photo.objects.get(pk=tmp_photos[0]).save()
                    request.session['tmp_photos']=[]
                if not ajax:
                    return HttpResponseRedirect('%s#do_listPlaces'%reverse('dashboard'))
        else:
            for e in form.errors:
                messages.error(request, e)
        if ajax:
            response = {
                'user':getattr(user,'username'),
                'loged_in':loged_in,
#                'new_place':repr(new_place),
                'errors':form.errors,
                'new_place_id':getattr(new_place,'id',0),
            }
            return HttpResponse(json.dumps(response), mimetype='application/json')


    else:
        form = addPlaceForm(instance=old_place)
        register_form = RegisterForm()
        login_form = LoginForm()
    str_fee =  _('%s%% Service Fee '% ghs.host_fee)
    context = {'form':form, 'rform':register_form,'lform':login_form,'place':old_place,
               'host_fee':ghs.host_fee, 'str_fee':str_fee, 'photos':photos,
    }
    return render_to_response(template_name, context, context_instance=RequestContext(request))


#def bannerxml(request, tip):
#    lang = request.LANGUAGE_CODE
#    context = {'slides': Vitrin.al_slide(banner_tip=tip, dilkodu=lang), }
#    ci = RequestContext(request)
#    return render_to_response('banner.xml', context, context_instance=ci)

#
#class IletisimForm(ModelForm):
#    class Meta:
#        model = Ileti
#        fields = ('gonderen_ad', 'gonderen_eposta', 'konu', 'yazi')
#
#
#def iletisim(request, urun_id=None):
#    lang = request.LANGUAGE_CODE
#    ilgili_urun_id = request.REQUEST.get('ilgili_urun')
#
##    urun = Urun.objects.get(pk=urun_id) if urun_id else None
#    urun = None
#    if request.method == 'POST':
#        form = IletisimForm(request.POST)
#        if form.is_valid():
#            i = form.save(commit=False)
#            i.ip = request.META.get('REMOTE_ADDR')
#
#            if urun:
#                tesk_msj='Ürünümüz hakkındaki mesajınız alındı. Teşekkür Ederiz.'
#                i.yazi = '%s adlı ürün hakkında;\n\n%s' % (urun.baslik(), i.yazi)
#            else:
#                tesk_msj='Mesajınız alındı. Teşekkür Ederiz.'
#            i.save()
#            messages.add_message(request, messages.INFO, tesk_msj)
#            return HttpResponseRedirect('/%s/mesaj_goster/'%lang)
#    else:
#        form = IletisimForm()
#        if urun:
#            form.fields['konu'].initial = urun.al_baslik(lang)
#    context = {'form': form,}
#    if urun:
#        context.update({'urun':urun,'icerik':urun.al_icerik(lang),
#                'kategoriler': urun.kategoriler(lang)})
#    elif request.GET.get('sayfa_id'):
#        context.update({'kategoriler':Sayfa.objects.get(pk=int(request.GET.get('sayfa_id'))).kategoriler(lang) })
#
#    ci = RequestContext(request)
#    return render_to_response('iletisim.html', context, context_instance=ci)


def icerik(request, id, slug):
    sayfa = get_object_or_404(Sayfa, pk=id)
    lang = request.LANGUAGE_CODE
    context = {'sayfa_id': sayfa.id, 'sayfa': sayfa,
               'icerik': sayfa.al_icerik(lang),
               'ust_baslik':sayfa.parent.al_baslik(lang),
               'kategoriler': sayfa.yansayfalar(lang)}
    ci = RequestContext(request)
    sablon = 'content_templates/' + (sayfa.sablon or 'icerik.html')
    return render_to_response(sablon, context, context_instance=ci)


def mesaj_goster(request):
    lang = request.LANGUAGE_CODE
    sayfa = Sayfa.al_anasayfa()
    context = {'sayfa': sayfa,'kategoriler': sayfa.kategoriler(lang)}
    ci = RequestContext(request)
    return render_to_response('content.html', context, context_instance=ci)


def haber_goster(request, id, slug):
    haber = get_object_or_404(Haber, pk=id)
    lang = request.LANGUAGE_CODE
    context = {'sayfa_id': haber.id, 'sayfa': haber,
               'icerik': {'metin': haber.icerik, 'baslik': haber.baslik},
               'kategoriler': haber.kategoriler(request.LANGUAGE_CODE)}
    ci = RequestContext(request)
    return render_to_response('content.html', context, context_instance=ci)


def dilsec(request, kod):
    url = request.GET.get('url')
    url = '/%s%s/' % (kod[:2], url[3:] if url else '/')
    return HttpResponseRedirect(url.replace('//', '/'))



@csrf_exempt
def multiuploader_delete(request, pk):
    """
    View for deleting photos with multiuploader AJAX plugin.
    made from api on:
    https://github.com/blueimp/jQuery-File-Upload
    """
    if request.method == 'POST':
        log.info('Called delete image. Photo id='+str(pk))
        image = get_object_or_404(Photo, pk=pk)
        if image.place and image.place.owner != request.user:
            return HttpResponseForbidden()
        image.delete()
        log.info('DONE. Deleted photo id='+str(pk))
        return HttpResponse(str(pk))
    else:
        log.info('Recieved not POST request todelete image view')
        return HttpResponseBadRequest('Only POST accepted')



def square_thumbnail(source, size=(50, 50)):
    thumbnail_options = dict(size=size, crop=True)
    return get_thumbnailer(source).get_thumbnail(thumbnail_options)

@csrf_exempt
def multiuploader(request, place_id=None):
    #FIXME : file type checking
    if request.method == 'POST':
        log.info('received POST to main multiuploader view')
        if request.FILES == None:
            return HttpResponseBadRequest('Must have files attached!')

        #getting file data for farther manipulations
        file = request.FILES[u'files[]']
        wrapped_file = UploadedFile(file)
        filename = wrapped_file.name
        file_size = wrapped_file.file.size
        log.info (u'Got file: %s'%filename)

        #writing file manually into model
        #because we don't need form of any type.

        image = Photo()
        image.name=str(filename)
        image.image=file
        if place_id:
            place = get_object_or_404(Place, pk=place_id)
            if place.owner != request.user:
                return HttpResponseForbidden()
            image.place = place
        image.save()
        if not place_id:
            tmp_photos = request.session.get('tmp_photos',[])
            tmp_photos.append(image.id)
            request.session['tmp_photos'] = tmp_photos
#        log.info('File saving done')

        #getting url for photo deletion
        file_delete_url = '/delete_photo/'

        #getting file url here
        file_url = image.image.url

        #getting thumbnail url using sorl-thumbnail
        im = square_thumbnail(image.image)
        thumb_url = im.url
#        thumb_tag = im.tag()

        #generating json response array
        result = []
        result.append({"name":filename,
                       "size":file_size,
                       "url":file_url,
#                       "tag":thumb_tag,
                       "turl":thumb_url,
                       "id":str(image.pk),
                       "delete_url":file_delete_url+str(image.pk),
                       "delete_type":"POST",})
        response_data = json.dumps(result)
        return HttpResponse(response_data, mimetype='application/json')

@csrf_exempt
def bookmark(request):
    if request.method == 'POST':
        place =Place.objects.get(pk=request.POST.get('pid'))
        profile = request.user.get_profile()
        if request.POST.get('remove'):
            profile.favorites.remove(place)
            result = 'removed'
        else:
            profile.favorites.add(place)
            result = 'added'
        profile.save()
        return HttpResponse([result], mimetype='application/json')

@csrf_exempt
def send_message_to_host(request):
    if request.method == 'POST' and request.POST.get('message'):

        place =Place.objects.get(pk=request.POST.get('pid'))
        owner = place.owner
        user = request.user
        msg = request.POST.get('message')
        msg = user.sent_messages.create(receiver=owner, text=msg, place=place)
        current_site = get_current_site(request)
        message = {
            'link': u'/dashboard/#do_showMessage,%s'% msg.id,
            'surname':owner.last_name,
            'domain':current_site.domain,
            'name':current_site.name
        }
        send_html_mail(_('You have a message'),
            owner.email,
            message,
            template='mail/new_message.html',
            recipient_name=owner.get_full_name())
        result = json.dumps({'message':force_unicode(_('Your message successfully sent.'))}, ensure_ascii=False)
        return HttpResponse(result, mimetype='application/json')

@csrf_exempt
def set_message(request,msg):
    if request.method == 'POST':
        messages.info(request, DJSTRANS['login_for_bookmark'])
    return HttpResponse([1], mimetype='application/json')


def image_view(request):
    items = Photo.objects.all()
    return render_to_response('images.html', {'items':items})

def statusCheck(request):
    context={
        'authenticated':request.user.is_authenticated(),
    }
    response =  HttpResponse(json.dumps(context), mimetype='application/json')
    response.set_cookie('lin', 1 if context['authenticated'] else -1)
    return response


def logout(request):
    auth.logout(request)
    return HttpResponseRedirect('/')

def login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        rform = RegisterForm(request.POST)
        if form.is_valid():
            user = auth.authenticate(username=form.cleaned_data['login_email'], password=form.cleaned_data['login_pass'])
            if user:
                if not request.POST.get('remember_me', None):
                    request.session.set_expiry(0)
                auth.login(request, user)
#                log.debug('login user "%s"'%user.get_profile().favorites.all())
#                profile = user.get_profile()
#                xxxxxxxxx=list(profile.favorites.values_list('id',flat=True))
#                assert 0,user.get_profile().favorites.values_list('id',flat=True)
                response =  HttpResponseRedirect(request.POST.get('next') or reverse('dashboard') )
                response.set_cookie('ganibookmarks',
                    str(user.get_profile().favorites.values_list('id',flat=True) ))
                return response
            else:
                messages.error(request, _('Wrong email or password.'))
    else:
        form = LoginForm()
        rform = RegisterForm()
    context = {'form':form, 'rform':rform}
    return render_to_response('login.html', context, context_instance=RequestContext(request))

def register(request,template='register.html'):
    sayfa = Sayfa.al_anasayfa()
    lang = request.LANGUAGE_CODE
    user = request.user
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        lform = LoginForm(request.POST)
        if form.is_valid():
            try:
                if form.cleaned_data['pass1']==form.cleaned_data['pass2']:
                    if User.objects.filter(username = form.cleaned_data['email']):
                        raise DatabaseError
#                        raise DatabaseError
                    user = form.save(commit=False)
                    user.username = user.email
                    user.set_password(form.cleaned_data['pass1'])
                    user.save()
                    return HttpResponseRedirect(reverse('registeration_thanks'))
                else:
                    messages.error(request, _('The passwords you entered do not match.'))
            except DatabaseError:
                messages.error(request, _('This email is already registered, please choose another one.'))
    else:
        form = RegisterForm()
        lform = LoginForm()
    context = {'form':form, 'lform':lform, 'next': request.GET.get('next','/')}
    return render_to_response(template, context, context_instance=RequestContext(request))


def registeration_thanks(request):
    context = {}
    return render_to_response('registeration_thanks.html', context, context_instance=RequestContext(request))

@csrf_exempt
def search(request):
    sresults = Place.objects.filter(active=True)
    form = SearchForm(request.REQUEST)
    lang = request.LANGUAGE_CODE
    amens = Tag.getTags(lang)
    context = {'form':form, 'amens':amens, 'place_types':PLACE_TYPES, 'space_types':SPACE_TYPES }
    return render_to_response('search.html', context, context_instance=RequestContext(request))

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

def parseJSData(request, key):
    data = request.POST.get(key)
    if data:
        return json.loads(data)
#        return [data] if type(data) not in (list, dict)  else data
    else:
        return []

@csrf_exempt
def search_ajax(request):
    form = SearchForm(request.REQUEST)
    pls = Place.objects.filter(active=True).distinct()
    page = request.GET.get('page',1)
    log.debug('search view')
#    pls = Place.objects.filter(q).values_list('neighborhood','district','city','state','country')
    if form.is_valid():
        log.debug('search valid')
        query = form.cleaned_data['query']
        cin = form.cleaned_data['checkin']
        cout = form.cleaned_data['checkout']
        nog = form.cleaned_data['no_of_guests']
        pls = pls.filter(capacity__gte=nog)

    selected_currency = int(request.POST.get('scurrency'))
    min = int(request.POST.get('pmin'))
    max = int(request.POST.get('pmax'))
    convert_factor = Currency.objects.get(pk=selected_currency).get_factor()
    if max < 500:
        max = max * convert_factor
        pls = pls.filter(gprice__lte=max)
    if min > 20:
        min = min * convert_factor
        pls = pls.filter(gprice__gte=min)
    amens = parseJSData(request,'ids_amens')
    if amens:
        for a in amens:
            pls = pls.filter(tags=a)
    stypes = parseJSData(request,'ids_stypes')
    if stypes:
        pls = pls.filter(space__in=stypes)
    ptypes = parseJSData(request,'ids_ptypes')
    if ptypes:
        pls = pls.filter(type__in=ptypes)
    if query:
        query = [q.strip() for q in query.split(',')[:2]]
        log.debug('query: %s'%query)
        q = Q()
        for qp in query:
            q = q & Q(state__istartswith=qp) | Q(city__istartswith=qp) | Q(district__istartswith=qp) | Q(neighborhood__istartswith=qp)
        pls = pls.filter(q)
    if cin and cout:
        pls  = pls.filter(~Q(reserveddates__start__lte=cin, reserveddates__end__gte=cin) &
                          ~Q(reserveddates__start__gte=cout, reserveddates__end__lte=cout))
#    paginator = Paginator(contact_list, 25)
    return HttpResponse(u'[%s]' % u','.join([p for p in pls.values_list('summary', flat=True)]),
        mimetype='application/json')
def cleandict(d):
     if not isinstance(d, dict):
         return d
     return dict((k,cleandict(v)) for k,v in d.iteritems() if v is not None)

def search_autocomplete(request):
    query = request.GET.get('q').split(' ')[:3]
    q = Q()
    for qp in query:
        q = q | Q(state__istartswith=qp) | Q(city__istartswith=qp) | Q(district__istartswith=qp) | Q(neighborhood__istartswith=qp)
    places = Place.objects.filter(q).values_list('neighborhood','district','city','state','country')
    nplaces = []
    for place in places:
        place = list(place)
        place[4] = force_unicode(COUNTRIES_DICT[place[4]])
        nplace = []
        for p in place:
            if not p: p = u''
            nplace.append(p)
            log.info('type of %s : %s' % (p, type(p)))
        nplaces.append(nplace)
#    places = [filter(None,p) for p in places]
    return HttpResponse(json.dumps(nplaces,  ensure_ascii=False), mimetype='application/json')


def paypal_complete(request):
    return render_to_response('paypal-compelete.html',{}, context_instance=RequestContext(request))

def paypal_cancel(request):
    return render_to_response('paypal-cancel.html',{}, context_instance=RequestContext(request))

@csrf_exempt
def book_place(request):


    if request.POST.get('placeid'):
        bi = request.POST.copy()
        request.session['booking_selection']=bi
    else:
        bi = request.session.get('booking_selection',{})

    if not request.user.is_authenticated():
        return HttpResponseRedirect('%s?next=%s?express=1'% (reverse('lregister'),reverse('book_place')))


    place = Place.objects.get(pk=bi['placeid'])
    ci = datetime.strptime(bi['checkin'],'%Y-%m-%d')
    co = datetime.strptime(bi['checkout'],'%Y-%m-%d')
    guests = bi['no_of_guests']
    crrid = bi['currencyid']
    crr,crrposition = Currency.objects.filter(pk=crrid).values_list('name','code_position')[0]
    prices = place.calculateTotalPrice(crrid,ci, co, guests)
    item = {"amt": str(prices['paypal']),             # amount to charge for item
              "inv": "AAAAAA",         # unique tracking variable paypal
              "custom": "BBBBBBBB",       # custom tracking variable for you
              "cancelurl": "%s%s" %(settings.SITE_NAME, reverse('paypal_cancel')),  # Express checkout cancel url
              "returnurl": "%s%s" %(settings.SITE_NAME, reverse('book_place')),}  # Express checkout return url

    kw = {"item": item,                            # what you're selling
        "payment_template": "book_place.html",      # template name for payment
        "confirm_template": "paypal-confirm.html", # template name for confirmation
        "success_url": reverse('paypal_complete')}              # redirect location after success
#paypal_dict = {
#        "business": settings.PAYPAL_RECEIVER_EMAIL,
#        "amount": prices['paypal'],
#        "item_name": "name of the item",
#        "invoice": "unique-invoice-id",
#        "notify_url": "%s%s" %(settings.SITE_NAME, reverse('paypal-ipn')),
#        "return_url": "%s%s" %(settings.SITE_NAME, reverse('paypal_complete')),
#        "cancel_return": "%s%s" %(settings.SITE_NAME, reverse('paypal_  cancel')),
#
#    }

#    form = PayPalPaymentsForm(initial=paypal_dict)
    #'form':form.sandbox()
    context ={'place':place, 'ci':ci, 'co':co,'ndays':bi['ndays'], 'guests':guests, 'prices': prices,
              'crr':crr,'crrpos':crrposition,}
    kw['context'] = context
#    return render_to_response('book_place.html',context, context_instance=RequestContext(request))
    ppp = PayPalPro(**kw)
    return ppp(request)


def server_error(request, template_name='500.html'):
    """
    500 error handler.

    Templates: `500.html`
    Context: None
    """
    return render_to_response(template_name,
        context_instance = RequestContext(request)
    )

from collections import defaultdict
def show_faqs(request):
    return render_to_response('faq.html',
            {'faq':Question.getFaqs(request.LANGUAGE_CODE)},
        context_instance=RequestContext(request))
