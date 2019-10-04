from django.contrib.auth import authenticate
from django.shortcuts import render
from django.views import View
from rest_framework import status, generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .serializers import PersonSerializer, LoginSerializer, SocialAuthSerializer
from .renderers import PersonJSONRenderer


# Create your views here.
class PersonAPIView(generics.CreateAPIView):
    permission_classes = (AllowAny, )
    serializer_class = PersonSerializer
    # renderer_classes = (PersonJSONRenderer)

    def post(self, request):
        # import pdb; pdb.set_trace()
        user = request.data.get('Person', {})
         

        # The create serializer, validate serializer, save serializer pattern
        # below is common and you will see it a lot throughout this course and
        # your own work later on. Get familiar with it.
        serializer = self.serializer_class(data=user)
        serializer.is_valid(raise_exception=True)
        # email = serializer.validated_data.get('email', None)
        # send_link(email)
        serializer.save()
        # person_ = data[user]
        # person_.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class PersonLoginAPIView(generics.CreateAPIView):
    permissions_classes = (AllowAny,)
    serializer_class = LoginSerializer

    def post(self, request):
        user = request.data.get('user', {})

        # Notice here that we do not call `serializer.save()` like we did for
        # the registration endpoint. This is because we don't actually have
        # anything to save. Instead, the `validate` method on our serializer
        # handles everything we need.
        serializer = self.serializer_class(data=user)
        # import pdb; pdb.set_trace()
        serializer.is_valid(raise_exception=True)
 
        return Response(serializer.data, status=status.HTTP_200_OK)


class SocialAuthenticationView(generics.CreateAPIView):
    """Social authentication."""
    permission_classes = (AllowAny,)
    serializer_class = SocialAuthSerializer
    # render_classes = (UserJSONRenderer,)

    def create(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        provider = request.data['provider']
        strategy = load_strategy(request)
        authenticated_user = request.user if not request.user.is_anonymous else None

        try:
            backend = load_backend(
                strategy=strategy,
                name=provider,
                redirect_uri=None
            )

            if isinstance(backend, BaseOAuth1):
                if "access_token_secret" in request.data:
                    token = {
                        'oauth_token': request.data['access_token'],
                        'oauth_token_secret':
                        request.data['access_token_secret']
                    }
                else:
                    return Response({'error':
                                    'Please enter your secret token'},
                                    status=status.HTTP_400_BAD_REQUEST)
            elif isinstance(backend, BaseOAuth2):
                token = serializer.data.get('access_token')
        except MissingBackend:
            return Response({
                'error': 'Please enter a valid social provider'
                }, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = backend.do_auth(token, user=authenticated_user)
        except (AuthAlreadyAssociated, IntegrityError):
            return Response({
                "errors": "You are already logged in with another account"},
                status=status.HTTP_400_BAD_REQUEST)
        except BaseException:
            return Response({
                "errors": "Invalid token"},
                 status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if user:
            user.is_active = True
            username = user.username
            email = user.email

        date = datetime.now() + timedelta(days=20)
        payload = {
            'email': email,
            'username': username,
            'exp': int(date.strftime('%s'))
        }
        user_token = jwt.encode(
            payload, settings.SECRET_KEY, algorithm='HS256')
        serializer = UserSerializer(user)
        serialized_details = serializer.data
        serialized_details["token"] = user_token
        return Response(serialized_details, status.HTTP_200_OK)
