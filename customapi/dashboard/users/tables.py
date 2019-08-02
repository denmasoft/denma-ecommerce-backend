from django_tables2 import A, Column, LinkColumn, TemplateColumn

from oscar.core.loading import get_class

DashboardTable = get_class('dashboard.tables', 'DashboardTable')


class UserTable(DashboardTable):
    check = TemplateColumn(
        template_name='dashboard/users/user_row_checkbox.html',
        verbose_name=' ', orderable=False)
    email = LinkColumn('dashboard:user-detail', args=[A('id')],
                       accessor='email')
    name = Column(accessor='get_full_name',
                  order_by=('last_name', 'first_name'))
    active = Column(accessor='is_active')
    staff = Column(accessor='is_staff')
    date_registered = Column(accessor='date_joined')
    num_orders = Column(accessor='orders.count', orderable=False)
    actions = TemplateColumn(
        template_name='dashboard/users/user_row_actions.html',
        verbose_name=' ')

    icon = "group"

    class Meta(DashboardTable.Meta):
        template = 'dashboard/users/table.html'


class LicenseTable(DashboardTable):
    check = TemplateColumn(
        template_name='dashboard/users/license_row_checkbox.html',
        verbose_name=' ', orderable=False)
    board = Column(accessor='board')
    occupation = Column(accessor='occupation')
    licensee = Column(accessor='licensee')
    doing_business_as = Column(accessor='doing_business_as')
    cls = Column(accessor='cls')
    line1 = Column(accessor='line1')
    line2 = Column(accessor='line2')
    line3 = Column(accessor='line3')
    city = Column(accessor='city')
    state = Column(accessor='state')
    zipcode = Column(accessor='zipcode')
    county = Column(accessor='county')
    license_number = Column(accessor='license_number')
    alternate_license_number = Column(accessor='alternate_license_number')
    primary_status = Column(accessor='primary_status')
    secondary_status = Column(accessor='secondary_status')
    date_licensed = Column(accessor='date_licensed')
    effective_date = Column(accessor='effective_date')
    expiration_date = Column(accessor='expiration_date')
    military = Column(accessor='military')

    icon = "group"

    class Meta(DashboardTable.Meta):
        template = 'dashboard/users/license_table.html'