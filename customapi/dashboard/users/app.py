from django.conf.urls import url

from oscar.core.application import DashboardApplication
from oscar.core.loading import get_class


class UserManagementApplication(DashboardApplication):
    name = None
    default_permissions = ['is_staff', ]

    index_view = get_class('dashboard.users.views', 'IndexView')
    license_view = get_class('dashboard.users.views', 'WholeSaleLicenseView')
    import_licenses = get_class('dashboard.users.views', 'ImportLicenseView')
    user_detail_view = get_class('dashboard.users.views', 'UserDetailView')
    password_reset_view = get_class('dashboard.users.views',
                                    'PasswordResetView')
    alert_list_view = get_class('dashboard.users.views',
                                'ProductAlertListView')
    alert_update_view = get_class('dashboard.users.views',
                                  'ProductAlertUpdateView')
    alert_delete_view = get_class('dashboard.users.views',
                                  'ProductAlertDeleteView')

    def get_urls(self):
        urls = [
            url(r'^$', self.index_view.as_view(), name='users-index'),
            url(r'^wholesale-licenses/$', self.license_view.as_view(), name='license-index'),
            url(r'^import-licenses/$', self.import_licenses.as_view(), name='import-licenses'),
            url(r'^(?P<pk>-?\d+)/$',
                self.user_detail_view.as_view(), name='user-detail'),
            url(r'^(?P<pk>-?\d+)/password-reset/$',
                self.password_reset_view.as_view(),
                name='user-password-reset'),

            # Alerts
            url(r'^alerts/$',
                self.alert_list_view.as_view(),
                name='user-alert-list'),
            url(r'^alerts/(?P<pk>-?\d+)/delete/$',
                self.alert_delete_view.as_view(),
                name='user-alert-delete'),
            url(r'^alerts/(?P<pk>-?\d+)/update/$',
                self.alert_update_view.as_view(),
                name='user-alert-update'),
        ]
        return self.post_process_urls(urls)


application = UserManagementApplication()
