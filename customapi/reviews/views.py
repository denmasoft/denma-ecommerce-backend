# # -*- coding: utf-8 -*-
# from __future__ import unicode_literals
#
# from rest_framework import generics
# from rest_framework.permissions import  (IsAuthenticated,AllowAny)
# from rest_framework.response import Response
#
# from customapi.reviews.serializers import ProductReviewSerializer
#
#
#
# class ReviewList(generics.ListAPIView):
#     serializer_class = ProductReviewSerializer
#     permission_classes = AllowAny
#
#     def get(self, request, *args, **kwargs):
#         #TODO
#
#
#
#
# class ReviewDetail(generics.CreateAPIView):
#     serializer_class = ProductReviewSerializer
#     permission_classes =  IsAuthenticated
#
#     def post(self, request, *args, **kwargs):
#         #TODO
#
#
#
#
#
#
#
#
