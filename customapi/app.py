from django.conf.urls import url
from oscarapi.app import RESTApiApplication

from customapi.products  import views  as products_views
from customapi.categories import  views as categories_views
from customapi.wishlist import views as wishlist_views
from customapi.payments import views as payments_views
from customapi.api import views as root_views
from customapi.cart import views as cart_views
from rest_framework.authtoken import views as token_views
from customapi.user import views as user_views
from customapi.license import views as license_views

from oscarapi import views


class MyRESTApiApplication(RESTApiApplication):

    def get_urls(self):

        urls = [
            url(r'^load/products/$', categories_views.LoadMoreProducts.as_view(), name='load-products'),
            url(r'^get-slugs/$', categories_views.GenerateSlugs.as_view(), name="get-slugs"),
            url(r'^reset-orders/$', cart_views.ResetOrders.as_view(), name="reset-orders"),
            url(r'^encrypt/card/$', user_views.EncryptCardView.as_view(), name="encrypt-card"),
            url(r'^decrypt/card/$', user_views.DecryptCardView.as_view(), name="decrypt-card"),
            url(r'^test/email/$', user_views.FakeEmailView.as_view(), name="test-email"),
            url(r'^customer/register/$', user_views.CustomerRegisterView.as_view(), name="user-register"),
            url(r'^customer/(?P<pk>[0-9]+)/orders/$', user_views.UserPurchaseHistory.as_view(), name="customer-orders"),
            url(r'^recover/password/$', user_views.RecoverPasswordView.as_view(), name="recover-password"),
            url(r'^reset/password/$', user_views.ResetPasswordView.as_view(), name="reset-password"),
            url(r'^contact/$', user_views.SendContactView.as_view(), name="api-customer-contact"),
            url(r'^facebook-login/$', user_views.FacebookLoginView.as_view(), name="facebook-login"),
            url(r'^facebook/callback/$', user_views.FacebookCallbackView.as_view(), name="facebook-callback"),
            url(r'^google-login/$', user_views.GoogleLoginView.as_view(), name="google-login"),
            url(r'^google/callback/$', user_views.GoogleCallbackView.as_view(), name="google-callback"),
            url(r'^wholesale/licenses/$', license_views.WholesaleLicense.as_view(), name="wholesale-license"),
            url(r'^login/$', user_views.CustomerLoginView.as_view(), name='api-login'),
            url(r'^subscribe/$', user_views.SubscribeUserView.as_view(), name='newsletter-subscribe'),
            url(r'^customer/logout/$', user_views.CustomerLogoutView.as_view(), name="customer-logout"),
            url(r'^remove-address/$', user_views.RemoveUserAddress.as_view(), name="remove-address"),
            url(r'^customer/profile/$', user_views.CustomerProfileView.as_view(),
                name="customer-profile"),
            url(r'^review-product/$', products_views.ReviewProduct.as_view(), name="review-product"),
               # CUSTOM APIS
            url(r'^countries/$', user_views.CountryList.as_view(), name='country-list'),
                url(r"^paypal/(?P<pk>[0-9]+)/$", cart_views.PayPalView.as_view(), name='paypal-payment'),
                url(r"^stripe/(?P<pk>[0-9]+)/$", cart_views.StripeView.as_view(), name='stripe-payment'),
                url(r"^paypal/(?P<pk>[0-9]+)/execute/$", cart_views.PaymentExecute.as_view(), name='paypal-execute'),
                url(r"^stripe/(?P<pk>[0-9]+)/execute/$", cart_views.StripeChargeView.as_view(), name='stripe-execute'),
                url(r'^cart/add-product/$', cart_views.CustomCartAddProduct.as_view(), name='api-cart-add-product'),
                url(r'^cart/shipping-rates/$', cart_views.CartShippingRates.as_view(), name='api-cart-shipping-rates'),
                url(r'^cart/checkout/$', cart_views.CartCheckout.as_view(), name='api-cart-checkout'),
                url(r'^cart/remove-product/$', cart_views.CustomCartRemoveProduct.as_view(),
                    name='api-cart-remove-product'),
                url(r'^baskets/(?P<pk>[0-9]+)/lines/$', cart_views.CustomLineList.as_view(), name='basket-lines-list'),
                url(r'^api-token-auth/', token_views.obtain_auth_token, name='api-token-auth'),
               url(r'^paymenttypes$', payments_views.SourceTypeList.as_view(),name='sourcetype-list'),
               url(r'^categories/$', categories_views.CategoryList.as_view(), name='category-list'),
                url(r'^find/products/$', categories_views.SearchProducts.as_view(), name='find-products'),
               url(r'^categories/children/(?P<pk>[0-9]+)/$', categories_views.ChildrenByCategory.as_view(), name='category-children'),
	       url(r'^categories/by/(?P<pk>[0-9]+)/$', categories_views.ByCategory.as_view(), name='category-by'),
               url(r'^products/$', products_views.ProductList.as_view(), name='products-list'),
               url(r'^products/(?P<pk>[0-9]+)/$', products_views.ProductDetail.as_view(),name='products-detail'),
               url(r'^products/category/(?P<pk>[0-9]+)/$',products_views.ProductListCategory.as_view(),name='products-by-category'),
               url(r'^products/search/(?P<pattern>[\w .-]+)/$', products_views.ProductListSearch.as_view(),name='products-by-search'),
            url(r'^checkout/$', cart_views.CartCheckoutView.as_view(), name='api-checkout'),
            url(r'^basket/$', cart_views.CustomBasketView.as_view(), name='api-basket'),
            url(r'^baskets/(?P<pk>[0-9]+)/$', cart_views.CustomBasketDetail.as_view(), name='basket-detail'),
            url(r'^wishlist/$', wishlist_views.WishListView.as_view(), name='api-wishlist'),
            url(r'^wishlists/(?P<pk>[0-9]+)/$', wishlist_views.WishListLineList.as_view(), name='wishlist-detail'),
            url(r'^wishlists/(?P<pk>[0-9]+)/add-product/$', wishlist_views.CustomWishListAddProduct.as_view(),
                name='wishlist-add-product'),
            url(r'^wishlist/add-product/$', wishlist_views.CustomWishListAddProd.as_view(),
                name='wishlist-add-prod'),
            url(r'^wishlists/(?P<pk>[0-9]+)/remove-product/$', wishlist_views.CustomWishListRemoveProduct.as_view(),
                name='wishlist-remove-product'),
            url(r'^wishlist/remove-product/$', wishlist_views.CustomWishListRemoveProd.as_view(),
                name='wishlist-remove-prod'),
            url(r'^wishlist/add-to-basket/$', wishlist_views.AddToBasketFromWishlist.as_view(),
                name='api-wishlist-add-to-basket'),
               #API ROOT
               url(r'^$', root_views.api_root, name='api'),
        ]

        return urls + super(MyRESTApiApplication, self).get_urls()

application = MyRESTApiApplication()
