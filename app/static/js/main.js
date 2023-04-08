
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

function validateCronTime(cronTime) {
    const regex = /^(\*|(?:[0-5]?\d)(?:-[0-5]?\d)?)(?:\/(\d+))?$/;
    const timeArray = cronTime.split(' ');
  
    if (timeArray.length !== 5) {
      return false;
    }
  
    for (let i = 0; i < timeArray.length; i++) {
      if (!regex.test(timeArray[i])) {
        return false;
      }
    }
  
    return true;
}

$(document).ready(function(){
    // click on button submit
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
                x: 30,
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
    $('.DMSChecker').change(function() {
        var selectedId = $(this).find("option:selected").attr("dms_id");
        var $data = {"dms_id":selectedId};
        $.ajax({
            url: 'jobs/getDatabases',
            type: "POST",
            dataType: 'json',
            data: JSON.stringify($data),
            headers: {
                'X-CSRFToken': getCookie("csrftoken"),
            },
            contentType: 'application/json;charset=UTF-8', // post data || get data
            success : function(result) {
                if (result.status == "200") {
                    var hashtagDiv = $(".hashtag_div");
                    hashtagDiv.empty();
                    for (var i = 0; i < result.databases.length; i++) {
                        var newSpan = $("<span class='btn btn-primary hashtags'>" + result.databases[i] + "</span>");
                        hashtagDiv.append(newSpan);
                    }
                    $('input[data-role="tagsinput"]').tagsinput();

                    $('.hashtags').on('click', function() {
                    var hashtagText = $(this).text();
                    var input = $('input[data-role="tagsinput"]');

                    input.tagsinput('add', "<span class='hashtags'>" + result.databases[i] + "</span>");
                    });
                } else {
                    hashtagDiv.empty();
                    hashtagDiv.append("<span>Type your own databases</span>");
                    notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', ' ', result.error);
                }
            },
            error: function(xhr, resp, text) {
                var hashtagDiv = $(".hashtag_div");
                hashtagDiv.empty();
                hashtagDiv.append("<span>Type your own databases</span>");
                notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' Can not connect to walnut django server');
            }
        })

        // если выбрана определенная опция, показываем extraField
        if ($(this).val().split('/')[0] === 'mssql') {
            $('.mssql-extra-field').show();
        } else {
            $('.mssql-extra-field').hide();
        }
      });
    $('#editJob').on('show.bs.modal', function (event) {
        if ($('#JobFormDMSEdit').val().split('/')[0] === 'mssql') {
            $('.mssql-extra-field').show();
        } else {
            $('.mssql-extra-field').hide();
        }
    });
    $('#AddJob').on('show.bs.modal', function (event) {
        if ($('#JobFormDMSAdd').val().split('/')[0] === 'mssql') {
            $('.mssql-extra-field').show();
        } else {
            $('.mssql-extra-field').hide();
        }
    });
    $("#AddDMSSubmit").on('click', function(){
        var $data = {};
        $('#AddDMSForm').find ('input, textearea, select').each(function() {
            $data[this.name] = $(this).val();
        });
        $.ajax({
            url: 'dms/optionsDMS',
            type: "POST",
            dataType: 'json',
            data: JSON.stringify($data),
            headers: {
                'X-CSRFToken': getCookie("csrftoken"),
            },
            contentType: 'application/json;charset=UTF-8', // post data || get data
            success : function(result) {
                if (result.status == "200") {
                    location.reload();
                } else if (result.error) {
                    notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' ' + result.error);
                } else {
                    notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' Server error');
                }
            },
            error: function(xhr, resp, text) {
                notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' Can not connect to walnut django server');
            }
        })
    });
    $("#AddJobSubmit").on('click', function(){
        var $data = {};
        $('#AddJobForm').find ('input, textearea, select').each(function() {
            if (this.name == "dst_db") {
                $data[this.name] = this.options[this.selectedIndex].id
            } else {
                $data[this.name] = $(this).val();
            };
        });
        if (validateCronTime($data["frequency"])) {
            $.ajax({
                url: 'jobs/optionsJob',
                type: "POST",
                dataType: 'json',
                data: JSON.stringify($data),
                headers: {
                    'X-CSRFToken': getCookie("csrftoken"),
                },
                contentType: 'application/json;charset=UTF-8', // post data || get data
                success : function(result) {
                    if (result.status == "200") {
                        location.reload();
                    } else {
                        notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', result.error);
                    }
                },
                error: function(xhr, resp, text) {
                    notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' Can not connect to walnut django server');
                }
            })
        } else {
            notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' Incorrect frequency format');
        }
    });
    // init clickTriggerOnTimeout
    $('.startJob').off('click', clickTriggerOnTimeout).on('click', clickTriggerOnTimeout);

    // clickTriggerOnTimeout function
    function clickTriggerOnTimeout ( event ) {
        var $this = $(this);

        if ( !$this.length || $this.hasClass('disabled') || $this.prop('disabled') ) return;

        event.preventDefault();

        var $thisMethod = 'POST',
            $thisDataType = 'JSON',
            $thisData = JSON.stringify({
                'id': $this[0].id
            }),
            $thisHeaders = {
                'X-CSRFToken': getCookie('csrftoken'),
            },
            $thisContentType = 'application/json;charset=UTF-8',
            $thisUrl = 'jobs/startJob',
            $thisClickTimeout = null;

        $.ajax({
            url: $thisUrl,
            type: $thisMethod,
            dataType: $thisDataType,
            data: $thisData,
            headers: $thisHeaders,
            contentType: $thisContentType,
            success: function (result) {
                if ( result ) {
                    if ( result.status === '200' ) {
                        notify('top', 'right', 'feather icon-layers', 'success', 'pass', 'pass', '', 'Job statred');
                        jobTrigger(2000);
                    }
                    else {
                        notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', result.error);
                        jobTrigger(0);
                    }
                }
                else {
                    notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', 'XHR Job server callback error');
                    jobTrigger(0);
                }

                function jobTrigger(timeout) {
                    $this.addClass('disabled').removeClass('startJob');
                    clearTimeout( $thisClickTimeout );
                    $thisClickTimeout = setTimeout(function () {
                        $this.removeClass('disabled').addClass('startJob');
                    }, timeout);
                }
            },
            error: function () {
                alert('XHR Job request error');
            }
        });
        
    }
    $('.job-status-switch').on('change', function () {
        var $data = {"id":this.id,"status":$(this).is(':checked')}; 
        $.ajax({
            url: 'jobs/statusJob',
            type: "POST",
            dataType: 'json',
            data: JSON.stringify($data),
            headers: {
                'X-CSRFToken': getCookie("csrftoken"),
            },
            contentType: 'application/json;charset=UTF-8', // post data || get data
            success : function(result) {
                if (result.status == "200") {
                    notify('top', 'right', 'feather icon-layers', 'success', 'pass', 'pass', '', ' Seccess');
                } else {
                    notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', result.error);
                }
            },
            error: function(xhr, resp, text) {
                notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' Can not connect to walnut django server');
            }
        })
    });
    
    $("#AddUserSubmit").on('click', function(){
        var $data = {};
        $('#AddUser').find ('input, textearea, select').each(function() {
            $data[this.name] = $(this).val();
        });
        if ($data["password"] == $data["repeat_password"]) {
            $.ajax({
                url: 'users/optionsUser',
                type: "POST",
                dataType: 'json',
                data: JSON.stringify($data),
                headers: {
                    'X-CSRFToken': getCookie("csrftoken"),
                },
                contentType: 'application/json;charset=UTF-8', // post data || get data
                success : function(result) {
                    if (result.status == "200") {
                        location.reload();
                    } else {
                        notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', ' ', result.error);
                    }
                },
                error: function(xhr, resp, text) {
                    notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' Can not connect to walnut django server');
                }
            })
        } else {
            notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', 'Passwords don\'t match');
        }
        
    });
    $(".dropdown_table").on('click', function(){
        $self = this
        if ($.inArray("show-table", $("#table_"+$self.id.split("_")[1]+ " tbody").attr("class").split(" ")) == -1) {
            $("#table_"+$self.id.split("_")[1] + " tbody").addClass("show-table")
            $("#table_"+$self.id.split("_")[1]).removeClass("backup-table")
        } else {
            $("#table_"+$self.id.split("_")[1]).addClass("backup-table")
            $("#table_"+$self.id.split("_")[1] + " tbody").removeClass("show-table")
        };
    });
    $("#JobFormDMSAdd").on("change", function() {
        var selectedId = $(this).find("option:selected").attr("id");
        var $data = {"dms_id":selectedId};
        console.log(selectedId)
        // Отправка POST-запроса на сервер

        $.ajax({
            url: 'jobs/getDatabases',
            type: "POST",
            dataType: 'json',
            data: JSON.stringify($data),
            headers: {
                'X-CSRFToken': getCookie("csrftoken"),
            },
            contentType: 'application/json;charset=UTF-8', // post data || get data
            success : function(result) {
                if (result.status == "200") {
                    var hashtagDiv = $(".hashtag_div");
                    hashtagDiv.empty();
                    for (var i = 0; i < result.databases.length; i++) {
                        var newSpan = $("<span class='hashtags btn btn-primary hashtags'>" + result.databases[i] + "</span>");
                        hashtagDiv.append(newSpan);
                    }
                    $('input[data-role="tagsinput"]').tagsinput();

                    $('.hashtags').on('click', function() {
                    var hashtagText = $(this).text();
                    var input = $('input[data-role="tagsinput"]');

                    input.tagsinput('add', hashtagText);
                    });
                } else {
                    notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', ' ', result.error);
                }
            },
            error: function(xhr, resp, text) {
                notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' Can not connect to walnut django server');
            }
        })
    });

});
