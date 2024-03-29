from django.conf.urls import url
from CrackSite import settings
from django.contrib.staticfiles.urls import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns


from CrackViewer import views

urlpatterns = [
    url(r'^upload/', views.upload, name='upload'),
    url(r'^upload_without_gt/', views.upload_without_gt, name='upload_without_gt'),

    url(r'^imagelist/', views.image_list, name='imagelist'),

    url(r'^imagedetail/(?P<image_pk>\d+)/$', views.image_detail, name='imagedetail'),

    # jquery
    url(r'^get_cracks/', views.get_cracks, name='get_cracks'),
    url(r'^get_regions/', views.get_regions, name='get_regions'),
    url(r'^get_seg_images/', views.get_seg_images, name='get_seg_images'),
    url(r'^get_patching/', views.get_patching, name='get_patching'),
    url(r'^analysis/', views.analysis, name='analysis'),
    url(r'^get_image_result/', views.get_image_result, name='get_image_result')
]

urlpatterns += staticfiles_urlpatterns()
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)