# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseForbidden
from django.core.files.base import ContentFile
from django.views.decorators.csrf import csrf_exempt
from .forms import ImageGTUploadForm, ImageUploadForm
from .models import *
from .utils.AnalysisRequest import AnalysisRequest
from CrackSite import settings

from PIL import Image
from io import BytesIO, StringIO
import json, os, base64
import cv2

@csrf_exempt
def upload(request) :
    if request.method == "POST" :
        form = ImageGTUploadForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()

            return redirect('/imagelist/')
        else :
            return redirect('/imagelist/')
    else :
        template_name = "upload.html"
        return render(request, template_name)

@csrf_exempt
def upload_without_gt(request) :
    if request.method == "POST" :
        form = ImageUploadForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            return redirect('/imagelist/')
        else :
            return redirect('/imagelist/')


def image_list(request) :
    image_model = ImageModel.objects.all().order_by('-pk')[:10]

    return render(request, 'imagelist.html', {'images' : image_model})

def image_detail(request, image_pk) :
    image = ImageModel.objects.filter(pk=image_pk)
    seg_result = SegResultModel.objects.filter(image=image_pk)
    seg_gt = SegGTModel.objects.filter(image=image_pk)
    is_analyzed = False
    is_gt = False
    seg_image_url = ""
    seg_image_th_url = ""
    if len(seg_result) > 0 :
        is_analyzed = True
        seg_image_url = str(seg_result[0].seg_image)
        seg_image_th_url = str(seg_result[0].seg_image_th)
    if len(seg_gt) > 0 :
        is_gt = True

    print(seg_image_url)
    print(seg_image_th_url)


    return render(request, 'imagedetail.html', {
                    'image': image[0],
                    'image_pk': image_pk,
                    'seg_result': seg_image_url,
                    'seg_th_result': seg_image_th_url,
                    'seg_gt':seg_gt,
                    'is_analyzed': is_analyzed,
                    'is_gt': is_gt
                })
@csrf_exempt
def get_cracks(request) :
    cracks = []
    if request.method == "POST" :
        cls_result = ClsResultModel.objects.filter(image__pk=request.POST['image_pk'])
        for crack in cls_result :
            dict_crack = {}
            dict_crack['label'] = crack.label
            dict_crack['x'] = crack.x
            dict_crack['y'] = crack.y
            dict_crack['w'] = crack.w
            dict_crack['h'] = crack.h
            dict_crack['severity'] = crack.severity
            cracks.append(dict_crack)
    return HttpResponse(json.dumps({"cracks": cracks}), 'application/json')

@csrf_exempt
def get_regions(request) :
    regions = []
    if request.method == "POST" :
        region_result = RegionResultModel.objects.filter(image__pk=request.POST['image_pk'])
        for region in region_result :
            dict_region = {}
            dict_region['region_num'] = region.region_num
            dict_region['region_type'] = region.region_type
            dict_region['patchs'] = []
            dict_region['severity_results'] = region.severity_results
            dict_region['patching_results'] = region.patching_results
            patchs = RegionPositionModel.objects.filter(region_model=region)
            for patch in patchs:
                dict_patch = {}
                dict_patch['label'] = patch.label
                dict_patch['x'] = patch.x
                dict_patch['y'] = patch.y
                dict_patch['w'] = patch.w
                dict_patch['h'] = patch.h
                dict_region['patchs'].append(dict_patch)
            regions.append(dict_region)
    return HttpResponse(json.dumps({"regions": regions}), 'application/json')

@csrf_exempt
def analysis(request) :
    result = []
    if request.method == "POST" :
        image = ImageModel.objects.filter(pk=request.POST['image_pk'])[0]
        image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../media/', str(image.image))

        # Send analysis request to crack-bridge-site
        analysis_request = AnalysisRequest()
        b_image = analysis_request.load_binary_image(image_path)

        region_connectivity = int(request.POST['region_connectivity'])
        region_noise_filter = int(request.POST['region_noise_filter'])
        severity_threshold = int(request.POST['severity_threshold'])
        analysis_request.set_request_attr(
            url='http://mltwins.sogang.ac.kr:8000/analyzer/',
            image=b_image, modules='crack',
            region_connectivity=region_connectivity,
            region_noise_filter=region_noise_filter,
            severity_threshold=severity_threshold,
        )
        response = json.loads((analysis_request.send_request_message().content).decode("utf-8"))['results'][0]['module_result']

        # Get classification result and segmentation result from response of crack-bridge-site
        cls_result = response['cls_result']
        seg_result = response['seg_image']
        region_results = response['region_result']

        for result in cls_result :
            clsResultModel = ClsResultModel.objects.create(image=image)

            label_list = []
            label_names = ['crack', 'lane', 'patch', 'normal']
            for label in result['label']:
                if label['description'] in label_names:
                    label_list.append(label)
            labels = sorted(label_list, key=lambda label_list: (label_list['score']), reverse=True)
            final_label = labels[0]['description']

            if labels[0]['description'] == 'crack':
                label_list = []
                detail_label_names = ['lc', 'tc', 'ac', 'detail_norm']
                for label in result['label']:
                    if label['description'] in detail_label_names:
                        label_list.append(label)
                labels = sorted(label_list, key=lambda label_list: (label_list['score']), reverse=True)
                if labels[0]['description'] == 'detail_norm':
                    final_label = 'normal'
                else:
                    final_label = labels[0]['description']

            clsResultModel.label = final_label
            clsResultModel.x = result['position']['x']
            clsResultModel.y = result['position']['y']
            clsResultModel.w = result['position']['w']
            clsResultModel.h = result['position']['h']
            if final_label in ['lc', 'tc', 'ac'] :
                clsResultModel.severity = result['severity']
            clsResultModel.save()

        # print(region_results)
        for region in region_results :
            region_area = region['region_area']
            regionResultModel = RegionResultModel.objects.create(image=image)
            regionResultModel.region_num = region['region']
            regionResultModel.region_type = region['region_type']
            if region['region_type'] in ['lc', 'tc', 'ac'] :
                severity_results = {}
                severity_results['total_max_width'] = region['total_max_width']
                severity_results['total_average_width'] = region['total_average_width']
                severity_results['max_width_x'] = region['max_width_x']
                severity_results['max_width_y'] = region['max_width_y']
                severity_results['maxx'] = region['maxx']
                severity_results['maxy'] = region['maxy']
                severity_results['minx'] = region['minx']
                severity_results['miny'] = region['miny']
                severity_results['severity'] = region['severity']
                regionResultModel.severity_results = severity_results
            elif region['region_type'] == 'patch' :
                patching_results = {}
                patching_results['area'] = region['area']
                patching_results['patching_bbox_minx'] = region['patching_bbox_minx']
                patching_results['patching_bbox_miny'] = region['patching_bbox_miny']
                patching_results['patching_bbox_maxx'] = region['patching_bbox_maxx']
                patching_results['patching_bbox_maxy'] = region['patching_bbox_maxy']
                patching_results['patching_region_minx'] = region['patching_region_minx']
                patching_results['patching_region_miny'] = region['patching_region_miny']
                patching_results['patching_region_maxx'] = region['patching_region_maxx']
                patching_results['patching_region_maxy'] = region['patching_region_maxy']
                patching_results['patching_seg_image'] = region['patching_seg_image']
                patching_results['contours'] = region['contours']
                regionResultModel.patching_results = patching_results
            else :
                print(region['region_type'])

            for patch in region_area :
                regionPositionModel = RegionPositionModel.objects.create(region_model=regionResultModel)

                regionPositionModel.x = patch['x']
                regionPositionModel.y = patch['y']
                regionPositionModel.w = patch['w']
                regionPositionModel.h = patch['h']
                regionPositionModel.save()
            regionResultModel.save()


        # Save segmentation result
        segResultModel = SegResultModel.objects.create(image=image)
        seg_img_path = os.path.join(str(image.image).split(".")[0] + "_seg" + ".png")
        seg_img_th_path = os.path.join(str(image.image).split(".")[0] + "_seg_th" + ".png")
        segResultModel.seg_image = ContentFile(base64.b64decode(seg_result), name=seg_img_path)
        segResultModel.seg_image_th = ContentFile(base64.b64decode(seg_result), name=seg_img_th_path)
        segResultModel.save()

        seg_img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../media/', seg_img_path)
        seg_img_th_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../media/', seg_img_th_path)
        seg_img = cv2.imread(seg_img_path, -1)
        seg_img_th = cv2.imread(seg_img_th_path, -1)

        seg_img[seg_img <= 127] = 0
        seg_img[seg_img > 127] = 255
        tmp = cv2.cvtColor(seg_img, cv2.COLOR_BGR2GRAY)
        _, alpha = cv2.threshold(tmp, 0, 127, cv2.THRESH_BINARY)
        b, g, r = cv2.split(seg_img)
        rgba = [b, g, r, alpha]
        seg_img = cv2.merge(rgba, 4)

        seg_img_th[seg_img_th <= severity_threshold] = 0
        seg_img_th[seg_img_th > severity_threshold] = 255
        tmp = cv2.cvtColor(seg_img_th, cv2.COLOR_BGR2GRAY)
        _, alpha = cv2.threshold(tmp, 0, 200, cv2.THRESH_BINARY)
        b, g, r = cv2.split(seg_img_th)
        rgba = [b, g, r, alpha]
        seg_img_th = cv2.merge(rgba, 4)

        cv2.imwrite(seg_img_path, seg_img)
        cv2.imwrite(seg_img_th_path, seg_img_th)

        return HttpResponse(json.dumps({"state": True}), 'application/json')
    else:
        return HttpResponse(json.dumps({"state": False}), 'application/json')