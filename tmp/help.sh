configure(){
        cert_help
        nginx_config
        echo "===============================================================================";
        echo "Please, check main config file";
        sleep 3;
        editor /etc/walnut/config.yaml
}

cert_help() {
        echo "----------------------"
        echo "| SSL SETUP          |"
        echo "----------------------"
        echo "Do you need help setting cerificate request?"
        select yn in "Yes" "No"; do
        case $yn in
        
                Yes ) 
                echo "===============================================================================";
                echo "Creating directory";
                mkdir -p /etc/nginx/certs/
                echo "===============================================================================";
                echo "Generating private key";
                openssl genrsa -out /etc/nginx/certs/private.key 4096
                echo -e "\nDone";
                echo "===============================================================================";
                echo "Edit request template";
                sleep 2;
                editor /tmp/walnut/req.cfg
                openssl req -new -config /tmp/walnut/req.cfg -key /etc/nginx/certs/private.key -out /tmp/walnut/certreq.csr -sha256
                echo "===============================================================================";
                echo "Would you like to use self-signed sertificate?"
                select yn in "Yes" "No"; do
                case $yn in
                        Yes) 
                        echo "===============================================================================";
                        sleep 2;
                        echo "Generating self-signed certificate";
                        openssl x509 -signkey /etc/nginx/certs/private.key -in /tmp/walnut/certreq.csr -req -days 3650 -out /etc/nginx/certs/cert.cer
                        break;;

                        No)
                        echo "===============================================================================";
                        cat /tmp/walnut/certreq.csr
                        echo -e "\nUse this request to obtain certificate from your certificate issuer\n Connect certificate into nginx config";
                        break;;
                esac
                done
                break;;

                No ) 
                echo "===============================================================================";
                echo -e "${RED}Walnut was disigned to work with https. Otherwise all of your credentials could be seen througth net${NC} \n";
                echo "You could use yout own configuration on nginx site proxypassing to this server ip 8000";
                break;;
        esac
        done

}

nginx_config() {
        echo "----------------------"
        echo "| NGINX CONF         |"
        echo "----------------------"
        echo "Check and edit nginx config";
                sleep 3;
        if cp -u /tmp/walnut/nginx.conf /etc/nginx/sites-available/walnut.conf; then
                ln -s /etc/nginx/sites-available/walnut.conf /etc/nginx/sites-enabled/ || true
                editor /etc/nginx/sites-enabled/walnut.conf
        else
                cp -u /tmp/walnut/nginx.conf /etc/nginx/conf.d/walnut.conf
                editor /etc/nginx/conf.d/walnut.conf
        fi
        if nginx -t; then
                systemctl reload nginx
        else
                echo -e "{$RED}SOMETHING WENT WRONG CHECK YOUR NGINX CONFIGURATION FILES{$NC} \n";
        fi
}