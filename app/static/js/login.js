
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

$(document).ready(function(){
    function notify(from, align, icon, type, animIn, animOut, title, message) {
        $.growl({
            icon: icon,
            title: title,
            message: message,
            url: ''
        }, {
            element: 'body',
            type: type,
            allow_dismiss: true,
            placement: {
                from: from,
                align: align
            },
            offset: {
                x: 50,
                y: 30
            },
            spacing: 10,
            z_index: 999999,
            delay: 2500,
            timer: 1000,
            url_target: '_blank',
            mouse_over: false,
            animate: {
                enter: animIn,
                exit: animOut
            },
            icon_type: 'class',
            template: '<div data-growl="container" class="alert" role="alert">' +
                '<button type="button" class="close" data-growl="dismiss">' +
                '<span aria-hidden="true">&times;</span>' +
                '<span class="sr-only">Close</span>' +
                '</button>' +
                '<span data-growl="icon"></span>' +
                '<span data-growl="title"></span>' +
                '<span data-growl="message"></span>' +
                '<a href="#!" data-growl="url"></a>' +
                '</div>'
        });
    };
    $("#LoginSubmit").on('click', function(){
        var $data = {};
        $('#loginForm').find ('input, textearea, select').each(function() {
            $data[this.name] = $(this).val();
        });
        $.ajax({
            url: '/login',
            type: "POST",
            dataType: 'json',
            headers: {
                'X-CSRFToken': getCookie("csrftoken"),
            },
            data: JSON.stringify($data),
            contentType: 'application/json;charset=UTF-8', // post data || get data
            success : function(result) {
                if (result.status == "200") {
                    window.location.replace("/");
                } else {
                    notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' Login error');
                }
                
            },
            error: function(xhr, resp, text) {
                notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' Login error');
            }
        });
    });
     $('input').keyup(function(e) {
        console.log("ok")
        if (e.which == 13) {
            var $data = {};
            $('#loginForm').find ('input, textearea, select').each(function() {
                $data[this.name] = $(this).val();
            });
            $.ajax({
                url: '/login',
                type: "POST",
                dataType: 'json',
                headers: {
                    'X-CSRFToken': getCookie("csrftoken"),
                },
                data: JSON.stringify($data),
                contentType: 'application/json;charset=UTF-8', // post data || get data
                success : function(result) {
                    if (result.status == "200") {
                        window.location.replace("/");
                    } else {
                        notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' Login error');
                    }
                    
                },
                error: function(xhr, resp, text) {
                    notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' Login error');
                }
            });
          return false;    //<---- Add this line
        }
      });
      
});