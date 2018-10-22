from __future__ import print_function

# python
import datetime
import logging
import os
import traceback
from abc import ABCMeta

import jwt
from flask import Response as HttpResponse
from flask import redirect
from flask import request
# flask
from flask.views import MethodView
from flask_api import status

#
from .utilx import Util
# halolib
from ..const import HTTPChoice
from ..exceptions import MaxTryException, HaloError, HaloException
from ..logs import log_json
from ..settingsx import settingsx

settings = settingsx()
# aws
# other

# Create your views here.
logger = logging.getLogger(__name__)


class AbsBaseLinkX(MethodView):
    __metaclass__ = ABCMeta

    """
        View to list all users in the system.

        * Requires token authentication.
        * Only admin users are able to access this view.
        """

    the_html = ''
    the_tag = ''
    other_html = ''
    other_tag = ''

    user_languages = []
    user_locale = settings.LOCALE_CODE
    user_lang = settings.LANGUAGE_CODE

    def __init__(self, **kwargs):
        super(AbsBaseLinkX, self).__init__(**kwargs)

    def do_process(self, request, typer, vars, format=None):

        now = datetime.datetime.now()

        self.user_langs = request.headers.get('HTTP_ACCEPT_LANGUAGE', ['en-US', ])
        self.req_context = Util.get_req_context(request)
        self.correlate_id = self.req_context["x-correlation-id"]
        self.user_agent = self.req_context["x-user-agent"]
        error_message = None
        orig_log_level = 0

        if Util.isDebugEnabled(self.req_context, request):
            orig_log_level = logger.getEffectiveLevel()
            logger.setLevel(logging.DEBUG)
            logger.debug("DebugEnabled - in debug mode",
                         extra=log_json(self.req_context, Util.get_req_params(request)))

        # logger.debug("headers", extra=log_json(self.req_context, Util.get_headers(request)))

        logger.debug("environ", extra=log_json(self.req_context, os.environ))

        if settings.HALO_HOST is None and 'HTTP_HOST' in request.headers:
            settings.HALO_HOST = request.headers['HTTP_HOST']
            from halolib.ssm import set_app_param_config
            set_app_param_config(settings.AWS_REGION, settings.HALO_HOST)

        self.get_user_locale(request)
        logger.debug('process LANGUAGE:  ' + str(self.user_lang) + " LOCALE: " + str(self.user_locale),
                     extra=log_json(self.req_context))

        try:
            ret = self.process(request, typer, vars)
            total = datetime.datetime.now() - now
            logger.info("performance_data", extra=log_json(self.req_context,
                                                           {"type": "LAMBDA",
                                                            "milliseconds": int(total.total_seconds() * 1000)}))
            return ret

        except MaxTryException as e:  # if api not responding
            error_message = str(e)
            e.stack = traceback.format_exc()
            logger.error(error_message, extra=log_json(self.req_context, Util.get_req_params(request), e))

        except HaloError as e:  # if api not responding
            error_message = str(e)
            e.stack = traceback.format_exc()
            logger.error(error_message, extra=log_json(self.req_context, Util.get_req_params(request), e))

        except HaloException as e:  # if api not responding
            error_message = str(e)
            e.stack = traceback.format_exc()
            logger.error(error_message, extra=log_json(self.req_context, Util.get_req_params(request), e))

        except IOError as e:
            error_message = str(e)
            e.stack = traceback.format_exc()
            logger.error(error_message, extra=log_json(self.req_context, Util.get_req_params(request), e))

        except ValueError as e:
            error_message = str(e)
            e.stack = traceback.format_exc()
            logger.error(error_message, extra=log_json(self.req_context, Util.get_req_params(request), e))

        except ImportError as e:
            error_message = str(e)
            e.stack = traceback.format_exc()
            logger.error(error_message, extra=log_json(self.req_context, Util.get_req_params(request), e))

        except EOFError as e:
            error_message = str(e)
            e.stack = traceback.format_exc()
            logger.error(error_message, extra=log_json(self.req_context, Util.get_req_params(request), e))

        except KeyboardInterrupt as e:
            # logger.debug(self.logprefix + 'You cancelled the operation.')
            error_message = str(e)
            e.stack = traceback.format_exc()
            logger.error(error_message, extra=log_json(self.req_context, Util.get_req_params(request), e))

        except AttributeError as e:
            error_message = str(e)
            e.stack = traceback.format_exc()
            logger.error(error_message, extra=log_json(self.req_context, Util.get_req_params(request), e))

        except Exception as e:
            error_message = str(e)
            e.stack = traceback.format_exc()
            logger.error(error_message, extra=log_json(self.req_context, Util.get_req_params(request), e))
            # exc_type, exc_obj, exc_tb = sys.exc_info()
            # fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            # logger.debug('An error occured in '+str(fname)+' lineno: '+str(exc_tb.tb_lineno)+' exc_type '+str(exc_type)+' '+e.message)

        finally:
            self.process_finally(request, orig_log_level)

        total = datetime.datetime.now() - now
        logger.info("error performance_data", extra=log_json(self.req_context,
                                                             {"type": "LAMBDA",
                                                              "milliseconds": int(total.total_seconds() * 1000)}))
        # log_json(logger, self.req_context, logging.DEBUG, str(ret), Util.get_req_params(request))

        if settings.FRONT_WEB:
            return redirect("/" + str(status.HTTP_400_BAD_REQUEST))
        return HttpResponse({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)

    def process_finally(self, request, orig_log_level):
        if Util.isDebugEnabled(self.req_context, request):
            if logger.getEffectiveLevel() != orig_log_level:
                logger.setLevel(orig_log_level)
                logger.info("process_finally - back to orig:" + str(orig_log_level),
                            extra=log_json(self.req_context))

    def split_locale_from_request(self, request):
        locale = ''
        if request.headers.get("QUERY_STRING", ""):
            path = request.headers['QUERY_STRING']
            key = "_="
            if key in path:
                if "&" in path:
                    list = path.split("&")
                    for l in list:
                        param = l
                        if key in param:
                            vals = param.split("=")
                            if len(vals) > 1:
                                locale = vals[1]
                else:
                    vals = path.split("=")
                    if len(vals) > 1:
                        locale = vals[1]
        logger.debug('split_locale_from_request:  ' + str(locale), extra=log_json(self.req_context))
        return locale

        # es,ar;q=0.9,he-IL;q=0.8,he;q=0.7,en-US;q=0.6,en;q=0.5,es-ES;q=0.4

    def get_user_locale(self, request):
        locale = self.split_locale_from_request(request)
        if (not locale) or (locale == ''):
            if 'HTTP_ACCEPT_LANGUAGE' in request.headers:
                self.user_languages = request.headers.get('HTTP_ACCEPT_LANGUAGE', self.user_locale + ",")
                logger.debug('user_languages:  ' + str(self.user_languages), extra=log_json(self.req_context))
                arr = self.user_languages.split(",")
                for l in arr:
                    if "-" in l:
                        if ";" not in l:
                            self.user_locale = l
                        else:
                            self.user_locale = l.split(";")[0]
                        break
                    else:
                        continue
        else:
            self.user_locale = locale
        logger.debug('process LOCALE_CODE:  ' + str(self.user_locale), extra=log_json(self.req_context))
        if settings.GET_LANGUAGE:
            # translation.activate(self.user_locale)
            self.user_lang = self.user_locale.split("-")[0]  # translation.get_language().split("-")[0]
        logger.debug('process LANGUAGE_CODE:  ' + str(self.user_lang), extra=log_json(self.req_context))

    def get(self):
        vars = {}
        return self.do_process(request, HTTPChoice.get, vars, format)

    def post(self):
        vars = {}
        return self.do_process(request, HTTPChoice.post, vars, format)

    def put(self):
        vars = {}
        return self.do_process(request, HTTPChoice.put, vars, format)

    def patch(self):
        vars = {}
        return self.do_process(request, HTTPChoice.patch, vars, format)

    def delete(self):
        vars = {}
        return self.do_process(request, HTTPChoice.delete, vars, format)

    def process(self, request, typer, vars):
        """
        Return a list of all users.
        """

        if typer == HTTPChoice.get:
            return self.process_get(request, vars)

        if typer == HTTPChoice.post:
            return self.process_post(request, vars)

        if typer == HTTPChoice.put:
            return self.process_put(request, vars)

        if typer == HTTPChoice.patch:
            return self.process_patch(request, vars)

        if typer == HTTPChoice.delete:
            return self.process_delete(request, vars)

        return HttpResponse('this is a ' + str(typer) + ' on ' + self.get_view_name())

    def process_get(self, request, vars):
        return HttpResponse('this is process get on ' + self.get_view_name())

    def process_post(self, request, vars):
        return HttpResponse('this is process post on ' + self.get_view_name())

    def process_put(self, request, vars):
        return HttpResponse('this is process put on ' + self.get_view_name())

    def process_patch(self, request, vars):
        return HttpResponse('this is process patch on ' + self.get_view_name())

    def process_delete(self, request, vars):
        return HttpResponse('this is process delete on ' + self.get_view_name())

    """def get_the_template(self, request,html):
        return loader.get_template(html)

    def get_template(self, request):
        if Util.mobile(request):
            t = loader.get_template(self.the_html)
            the_mobile_web = self.the_tag
        else:
            t = loader.get_template(self.other_html)
            the_mobile_web = self.other_tag
        return t, the_mobile_web"""

    def get_client_ip(self, request):
        ip = request.headers.get('REMOTE_ADDR')
        logger.debug("get_client_ip: " + str(ip), extra=log_json(self.req_context))
        return ip

    def get_jwt(self, request):
        ip = self.get_client_ip(request)
        encoded_token = jwt.encode({'ip': ip}, settings.SECRET_JWT_KEY, algorithm='HS256')
        return encoded_token

    def check_jwt(self, request):  # return true if token matches
        ip = self.get_client_ip(request)
        encoded_token = request.GET.get('jwt', None)
        if not encoded_token:
            return False
        decoded_token = jwt.decode(encoded_token, settings.SECRET_JWT_KEY, algorithm='HS256')
        return ip == decoded_token['ip']

    def get_jwt_str(self, request):
        return '&jwt=' + self.get_jwt(request).decode()


from ..flask.mixinx import PerfMixinX


class PerfLinkX(PerfMixinX, AbsBaseLinkX):
    pass


##################################### test ##########################

from ..flask.mixinx import TestMixinX


class TestLinkX(TestMixinX, AbsBaseLinkX):
    pass