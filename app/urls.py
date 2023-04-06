# Copyright (c) 2023 Shvora Nikita, Livitsky Andrey
# This app, Ratsky Walnut, is licensed under the GNU General Public License version 3.0 (GPL 3.0).
# All source code, design, and other intellectual property rights of Ratsky Walnut, including but not limited to text, graphics, logos, images, and software, are the property of the Ratsky community and are protected by international copyright laws.
# Permission is hereby granted, free of charge, to any person obtaining a copy of this app and associated documentation files (the "App"), to deal in the App without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the App, and to permit persons to whom the App is furnished to do so, subject to the following conditions:
#  1 The above copyright notice and this permission notice shall be included in all copies or substantial portions of the App.
#  2 Any distribution of the App or derivative works must include a copy of the GPL 3.0 license.
#  3 The App is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the App or the use or other dealings in the App.
# For more information on the GPL 3.0 license, please visit https://www.gnu.org/licenses/gpl-3.0.en.html.
from django.urls import path

from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.Main_Page_View.as_view(), name="Main_page"),
    path('login', views.Login_Page_View.as_view(), name="login_page"),
    path('logout', views.Logout_Page_View.as_view(), name='logout_page'),
    path('jobs', views.Jobs_Page_View.as_view(), name="Jobs_page"),
    path('jobs/optionsJob', views.get_form_add_job, name="get_form_add_job"),
    path('jobs/statusJob', views.get_status_job, name="get_status_job"),
    path('jobs/startJob', views.start_job, name="start_job"),
    # path('jobs/getDatabases', views.get_databases, name="get_databases"),
    path('dms', views.DMS_Page_View.as_view(), name="DMS_page"),
    path('dms/optionsDMS', views.get_form_add_dms, name="get_form_add_dms"),
    path('object/editObject', views.get_edit_object_data, name="get_edit_object_data"),
    path('backup/search', views.Backup_Search_Page_View.as_view(), name="Backup_search_page"),
    path('backup/', views.Backup_Page_View.as_view(), name="Backup_page"),
    path('backup/optionsBackup', views.get_form_add_backup, name="get_form_add_backup"),
    path('backup/download/<int:id>', views.download_backup, name="download_backup"),
    path('status', views.Status_Page_View.as_view(), name="Status_page"),
    path('settings/config', views.Config_Page_View.as_view(), name="config_page"),
    path('settings/users', views.Users_Page_View.as_view(), name="users_page"),
    path('settings/users/optionsUser', views.get_form_add_user, name="get_form_add_user"),
    
]