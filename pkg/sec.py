#!/usr/bin/env python


''' Copyright (c) 2023 Shvora Nikita, Livitsky Andrey
 This app, Ratsky Walnut, is licensed under the GNU General Public License version 3.0 (GPL 3.0).
 All source code, design, and other intellectual property rights of Ratsky Walnut, including but not limited to text, graphics, logos, images, and software, are the property of the Ratsky community and are protected by international copyright laws.
 Permission is hereby granted, free of charge, to any person obtaining a copy of this app and associated documentation files (the "App"), to deal in the App without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the App, and to permit persons to whom the App is furnished to do so, subject to the following conditions:
  1 The above copyright notice and this permission notice shall be included in all copies or substantial portions of the App.
  2 Any distribution of the App or derivative works must include a copy of the GPL 3.0 license.
  3 The App is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the authors or copyright holders be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the App or the use or other dealings in the App.
 For more information on the GPL 3.0 license, please visit https://www.gnu.org/licenses/gpl-3.0.en.html.'''

import os
from cryptography.fernet import Fernet
import yaml
import ruamel.yaml

file = os.environ.get(f'WALNUT_CONF_PATH') or "/etc/walnut/config.yaml"



def secret_gen_config():
    with open(file, 'r') as f:
        data = ruamel.yaml.round_trip_load(f)

    if 'secret' not in data:
        key = Fernet.generate_key()
        data['secret'] = key.decode("utf-8")

    with open(file, 'w') as f:
        ruamel.yaml.round_trip_dump(data, f, indent=4)

class Cryptorator(Fernet):
    def __init__(self) -> None:
        with open(file) as f:
            config = yaml.safe_load(f)
        key = bytes(config['secret'],"utf-8")
        super().__init__(key)
        # super().init(Secret.key)

    def encrypt(self, passwd):
        token = super().encrypt(bytes(passwd,"utf-8"))
        return token.decode("utf-8")
         

    def decrypt(self, token):
        return super().decrypt(token).decode("utf-8")
        

if __name__=='__main__':
    secret_gen_config()
    c = Cryptorator()
    enc = c.encrypt("asdfklIJ4ti8OAISD(*$(#)($*%&*$()))")
    print(c.decrypt(enc))
