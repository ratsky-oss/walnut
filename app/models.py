# Copyright (c) 2023 Shvora Nikita, Livitsky Andrey
# This app, Ratsky Walnut, is licensed under the GNU General Public License version 3.0 (GPL 3.0).
# All source code, design, and other intellectual property rights of Ratsky Walnut, including but not limited to text, graphics, logos, images, and software, are the property of the Ratsky community and are protected by international copyright laws.
# Permission is hereby granted, free of charge, to any person obtaining a copy of this app and associated documentation files (the "App"), to deal in the App without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the App, and to permit persons to whom the App is furnished to do so, subject to the following conditions:
#  1 The above copyright notice and this permission notice shall be included in all copies or substantial portions of the App.
#  2 Any distribution of the App or derivative works must include a copy of the GPL 3.0 license.
#  3 The App is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the App or the use or other dealings in the App.
# For more information on the GPL 3.0 license, please visit https://www.gnu.org/licenses/gpl-3.0.en.html.
import datetime
from django.db import models

from pkg.sec import Cryptorator

# Creator - LVTSKY

class DestinationDatabase(models.Model):
    host = models.CharField(max_length=32)
    port = models.IntegerField()
    username = models.CharField(max_length=256)
    password = models.CharField(max_length=256)
    
    class Meta:
        unique_together = ('host', 'port')

    def save(self, *args, **kwargs):
        c = Cryptorator() 
        self.password = c.encrypt(self.password)
        super(DestinationDatabase, self).save(*args, **kwargs)
        del c
        
    def __str__(self):
        return self.host

class DMSInfo(models.Model):
    type = models.CharField(max_length=32)
    version = models.CharField(max_length=32)
    dst_db = models.ForeignKey(DestinationDatabase, on_delete=models.CASCADE)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['version', 'type'], name='unique_dms_combination'
            )
        ]

class Job(models.Model):
    actions = [
    ('b','backup'),
    ('r','restore')
    ]
    status = [
    ('e','enabled'),
    ('d','disabled')
    ]
    name = models.CharField(max_length=256, unique=True)
    dst_db = models.ForeignKey(DestinationDatabase, on_delete=models.CASCADE)
    db_name = models.CharField(max_length=256, null=True, default='all')
    action = models.CharField(choices=actions, max_length=2)
    status = models.CharField(choices=status, max_length=2, default='e')
    remote_path = models.CharField(max_length=2048, null=True)
    frequency = models.CharField(max_length=256, null=True)
    rotation = models.IntegerField() 

class BackupInfo(models.Model):
    job = models.ForeignKey(Job, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(max_length=256, blank=False, default=datetime.datetime.utcnow())
    fs_path= models.CharField(max_length=256)
