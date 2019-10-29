# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseForbidden
from django.core.files.base import ContentFile
from django.views.decorators.csrf import csrf_exempt
from .forms import ImageUploadForm
from .models import ImageModel, ClsResultModel, SegResultModel
from .utils.AnalysisRequest import AnalysisRequest
from CrackSite import settings

from PIL import Image
from io import BytesIO, StringIO
import json, os, base64

@csrf_exempt
def upload(request) :
    template_name = "upload.html"
    if request.method == "POST" :
        form = ImageUploadForm(request.POST, request.FILES)

        if form.is_valid():
            image = form.save()

            # Read image path
            image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../media/' ,str(image.image))

            # Send analysis request to crack-bridge-site
            analysis_request = AnalysisRequest()
            b_image = analysis_request.load_binary_image(image_path)
            analysis_request.set_request_attr(url='http://mltwins.sogang.ac.kr:8000/analyzer/', image=b_image, modules='crack')
            response = json.loads((analysis_request.send_request_message().content).decode("utf-8"))['results'][0]['module_result']

            # Get classification result and segmentation result from response of crack-bridge-site
            cls_results = response['classification_result']
            seg_result = response['image']

            # Define model variables
            segResultModel = SegResultModel.objects.create(image=image)

            # Save classification result
            for result in cls_results:
                clsResultModel = ClsResultModel.objects.create(image=image)
                clsResultModel.label = result['label'][0]['description']
                clsResultModel.x = result['position']['x']
                clsResultModel.y = result['position']['y']
                clsResultModel.w = result['position']['w']
                clsResultModel.h = result['position']['h']
                clsResultModel.save()

            # Save classification result
            seg_img_path = os.path.join(settings.MEDIA_ROOT, str(image.image).split(".")[0] + "_seg" + ".png")
            segResultModel.seg_image = ContentFile(base64.b64decode(seg_result), name=seg_img_path)
            segResultModel.save()

            return redirect('/imagelist/')
        else :
            return redirect('/imagelist/')
    else :
        template_name = "upload.html"
        return render(request, template_name)

def imagelist(request) :
    image_model = ImageModel.objects.all().order_by('-pk')[:10]

    return render(request, 'imagelist.html', {'images' : image_model})

def imagedetail(request, image_pk) :
    image = ImageModel.objects.filter(pk=image_pk)

@csrf_exempt
def get_cracks(request) :
    cracks = []
    if request.method == "POST" :
        cls_result = ClsResultModel.objects.filter(image__pk=request.POST['image_pk'])
        print(len(cls_result))
        for crack in cls_result :
            dict_crack = {}
            dict_crack['label'] = crack.label
            dict_crack['x'] = crack.x
            dict_crack['y'] = crack.y
            dict_crack['w'] = crack.w
            dict_crack['h'] = crack.h
            cracks.append(dict_crack)
    return HttpResponse(json.dumps({"cracks": cracks}), 'application/json')
