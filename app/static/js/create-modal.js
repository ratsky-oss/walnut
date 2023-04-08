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
    $(".AddJob").on('click', function(){
        var selectedId = $(".DMSChecker").find("option:selected").attr("dms_id");
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
                        var newSpan = $("<span class='btn btn-primary hashtags'>" + result.databases[i] + "</span>");
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
    $(".deleteDMS").on('click', function(){
        $(".deleteDMS-buttons").html(`<button type="button" class="btn btn-secondary" data-dismiss="modal">No</button><button type="button" id="deleteDMS_${this.id}" class="btn btn-primary deleteDMSAccept" data-dismiss="modal" aria-label="Close">Yes</button`)
        $(".deleteDMSAccept").on('click', function(){
            $dms_id = this.id.split('_')[1]
            $.ajax({
                url: 'dms/optionsDMS',
                type: "DELETE",
                dataType: 'json',
                data: JSON.stringify({'id':$dms_id}),
                headers: {
                    'X-CSRFToken': getCookie("csrftoken"),
                },
                contentType: 'application/json;charset=UTF-8', // post data || get data
                success : function(result) {
                    if (result.status == "200") {
                        $(`.dms_${$dms_id}`).remove()
                        notify('top', 'right', 'feather icon-layers', 'success', 'pass', 'pass', '', ' DMS deleted');
                    } else {
                        notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' ' + result.error);
                    }
                },
                error: function(xhr, resp, text) {
                    notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' Server error');
                }
            })
        });
    });
    $(".editDMS").on('click', function(){
        $(".editDMS-buttons").html(`<button type="button" class="btn btn-secondary" data-dismiss="modal">No</button><button type="button" id="editDMS_${this.id}" class="btn btn-primary editDMSAccept" data-dismiss="modal" aria-label="Close">Yes</button`)
        $.ajax({
            url: 'object/editObject',
            type: "POST",
            dataType: 'json',
            data: JSON.stringify({'form-type':'dms','id':this.id}),
            headers: {
                'X-CSRFToken': getCookie("csrftoken"),
            },
            contentType: 'application/json;charset=UTF-8', // post data || get data
            success : function(result) {
                $('.editDMSinput[name=type]').val(result.type);
                $('.editDMSinput[name=version]').val(result.version);
                $('.editDMSinput[name=host]').val(result.host);
                $('.editDMSinput[name=port]').val(result.port);
                $('.editDMSinput[name=username]').val(result.username);
                $('.editDMSinput[name=password]').val(result.password);
            },
            error: function(xhr, resp, text) {
                notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' Server error');
            }
        })
        $(".editDMSAccept").on('click', function(){
            $dms_id = this.id.split('_')[1]
            var $data = {};
            $('#editDMS').find ('input, textearea, select').each(function() {
                $data[this.name] = $(this).val();
            });
            $data["id"] = $dms_id
            $.ajax({
                url: 'dms/optionsDMS',
                type: "PUT",
                dataType: 'json',
                data: JSON.stringify($data),
                headers: {
                    'X-CSRFToken': getCookie("csrftoken"),
                },
                contentType: 'application/json;charset=UTF-8', // post data || get data
                success : function(result) {
                    if (result.status == "200") {
                        notify('top', 'right', 'feather icon-layers', 'success', 'pass', 'pass', '', ' DMS updated');
                        location.reload();
                    } else {
                        notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' ' + result.error);
                    }
                },
                error: function(xhr, resp, text) {
                    notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' Server error');
                }
            })
        });
    });
    $(".deleteJob").on('click', function(){
        $(".deleteJob-buttons").html(`<button type="button" class="btn btn-secondary" data-dismiss="modal">No</button><button type="button" id="deleteJob_${this.id}" class="btn btn-primary deleteJobAccept" data-dismiss="modal" aria-label="Close">Yes</button`)
        $(".deleteJobAccept").on('click', function(){
            $job_id = this.id.split('_')[1]
            $.ajax({
                url: 'jobs/optionsJob',
                type: "DELETE",
                dataType: 'json',
                data: JSON.stringify({'id':$job_id}),
                headers: {
                    'X-CSRFToken': getCookie("csrftoken"),
                },
                contentType: 'application/json;charset=UTF-8', // post data || get data
                success : function(result) {
                    if (result.status == "200") {
                        $(`.job_${$job_id}`).remove()
                        notify('top', 'right', 'feather icon-layers', 'success', 'pass', 'pass', '', ' Job deleted');
                    } else {
                        notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' ' + result.error);
                    }
                },
                error: function(xhr, resp, text) {
                    notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' Server error');
                }
            })
        });
    });
    $(".editJob").on('click', function(){
        $(".editJob-buttons").html(`<button type="button" class="btn btn-secondary" data-dismiss="modal">No</button><button type="button" id="editJob_${this.id}" class="btn btn-primary editJobAccept" data-dismiss="modal" aria-label="Close">Yes</button`)
        $.ajax({
            url: 'object/editObject',
            type: "POST",
            dataType: 'json',
            data: JSON.stringify({'form-type':'job','id':this.id}),
            headers: {
                'X-CSRFToken': getCookie("csrftoken"),
            },
            contentType: 'application/json;charset=UTF-8', // post data || get data
            success : function(result) {
                var input = $('input[data-role="tagsinput"]');
                $('.editJobinput[name=dst_db]').val(result.dst_db);
                $('.editJobinput[name=name]').val(result.name);
                input.tagsinput('removeAll');
                input.tagsinput('add', result.db_name);
                $('.editJobinput[name=rotation]').val(result.rotation);
                $('.editJobinput[name=frequency]').val(result.frequency);
                if ($('.DMSChecker').val().split('/')[0] === 'mssql') {
                    $('.mssql-extra-field').show();
                    $('.editJobinput[name=remote_path]').val(result.remote_path);
                } else {
                    $('.mssql-extra-field').hide();
                }
            },
            error: function(xhr, resp, text) {
                notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' Server error');
            }
        })
        var selectedId = $(".DMSChecker").find("option:selected").attr("dms_id");
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
                        var newSpan = $("<span class='btn btn-primary hashtags'>" + result.databases[i] + "</span>");
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
        $(".editJobAccept").on('click', function(){
            $job_id = this.id.split('_')[1]
            var $data = {};
            $('#editJob').find ('input, textearea, select').each(function() {
                if (this.name == "dst_db") {
                    $data[this.name] = this.options[this.selectedIndex].id
                } else {
                    $data[this.name] = $(this).val();
                };
            });
            $data["id"] = $job_id
            if ($data["db_name"].includes(',')){
                notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' You cannot add more than 1 database when editing!');
                return;
            }
            if (validateCronTime($data["frequency"])) {
                $.ajax({
                    url: 'jobs/optionsJob',
                    type: "PUT",
                    dataType: 'json',
                    data: JSON.stringify($data),
                    headers: {
                        'X-CSRFToken': getCookie("csrftoken"),
                    },
                    contentType: 'application/json;charset=UTF-8', // post data || get data
                    success : function(result) {
                        if (result.status == "200") {
                            location.reload();
                        } else if (result["error"]) {
                            notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' ' + result.error);
                        } else {
                            notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' Server error');
                        }
                    },
                    error: function(xhr, resp, text) {
                        notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' Server error');
                    }
                })
            } else {
                notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' Incorrect frequency format');
            }
        });
    });
    $(".deleteUser").on('click', function(){
        $(".deleteUser-buttons").html(`<button type="button" class="btn btn-secondary" data-dismiss="modal">No</button><button type="button" id="deleteUser_${this.id}" class="btn btn-primary deleteUserAccept" data-dismiss="modal" aria-label="Close">Yes</button`)
        $(".deleteUserAccept").on('click', function(){
            $user_id = this.id.split('_')[1]
            $.ajax({
                url: 'users/optionsUser',
                type: "DELETE",
                dataType: 'json',
                data: JSON.stringify({'id':$user_id}),
                headers: {
                    'X-CSRFToken': getCookie("csrftoken"),
                },
                contentType: 'application/json;charset=UTF-8', // post data || get data
                success : function(result) {
                    if (result.status == "200") {
                        $(`.user_${$user_id}`).remove()
                        notify('top', 'right', 'feather icon-layers', 'success', 'pass', 'pass', '', ' User deleted');
                    } else {
                        notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' ' + result.error);
                    }
                },
                error: function(xhr, resp, text) {
                    notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' Server error');
                }
            })
        });
    });
    $(".editUser").on('click', function(){
        $(".editUser-buttons").html(`<button type="button" class="btn btn-secondary" data-dismiss="modal">No</button><button type="button" id="editUser_${this.id}" class="btn btn-primary editUserAccept" data-dismiss="modal" aria-label="Close">Yes</button`)
        $(".editUserAccept").on('click', function(){
            var $data = {};
            $data['id'] = this.id.split('_')[1]
            $('#editUserForm').find ('input, textearea, select').each(function() {
                $data[this.name] = $(this).val();
            });
            if ($data["password"] == $data["repeat_password"]) {
                $.ajax({
                    url: 'users/optionsUser',
                    type: "PUT",
                    dataType: 'json',
                    data: JSON.stringify($data),
                    headers: {
                        'X-CSRFToken': getCookie("csrftoken"),
                    },
                    contentType: 'application/json;charset=UTF-8', // post data || get data
                    success : function(result) {
                        if (result.status == "200") {
                            notify('top', 'right', 'feather icon-layers', 'success', 'pass', 'pass', '', ' User updated');
                        } else {
                            notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' ' + result.error);
                        }
                    },
                    error: function(xhr, resp, text) {
                        notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' Server error');
                    }
                })
            } else {
                notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', 'Passwords don\'t match');
            }
        });
    });
    $(".deleteBackup").on('click', function(){
        $(".deleteBackup-buttons").html(`<button type="button" class="btn btn-secondary" data-dismiss="modal">No</button><button type="button" id="deleteBackup_${this.id}" class="btn btn-primary deleteBackupAccept" data-dismiss="modal" aria-label="Close">Yes</button`)
        $(".deleteBackupAccept").on('click', function(){
            $backup_id = this.id.split('_')[1]
            $.ajax({
                url: 'optionsBackup',
                type: "DELETE",
                dataType: 'json',
                data: JSON.stringify({'id':$backup_id}),
                headers: {
                    'X-CSRFToken': getCookie("csrftoken"),
                },
                contentType: 'application/json;charset=UTF-8', // post data || get data
                success : function(result) {
                    if (result.status == "200") {
                        $(`.backup_${$backup_id}`).remove()
                        notify('top', 'right', 'feather icon-layers', 'success', 'pass', 'pass', '', ' Backup deleted');
                    } else if (result.status == "450") {
                        $(`.backup_${$backup_id}`).remove()
                        notify('top', 'right', 'feather icon-layers', 'warning', 'pass', 'pass', '', ' ' + result.error);
                    } else {
                        notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' ' + result.error);
                    }
                },
                error: function(xhr, resp, text) {
                    notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' Server error');
                }
            })
        });
    });
    $(".rcyncBackup").on('click', function(){
        $(".rcyncBackup-buttons").html(`<button type="button" class="btn btn-secondary" data-dismiss="modal">No</button><button type="button" id="rcyncBackup_${this.id}" class="btn btn-primary rcyncBackupAccept" data-dismiss="modal" aria-label="Close">Go</button`)
        $(".rcyncBackupAccept").on('click', function(){
            var $data = {};
            $data['backup_id'] = this.id.split('_')[1]
            $('#rcyncBackupForm').find ('input, textearea, select').each(function() {
                $data[this.name] = $(this).val();
            });
            $.ajax({
                url: 'rcync',
                type: "POST",
                dataType: 'json',
                data: JSON.stringify($data),
                headers: {
                    'X-CSRFToken': getCookie("csrftoken"),
                },
                contentType: 'application/json;charset=UTF-8', // post data || get data
                success : function(result) {
                    if (result.status == "200") {
                        notify('top', 'right', 'feather icon-layers', 'success', 'pass', 'pass', '',  result.message);
                    } else if (result.status == "450") {
                        notify('top', 'right', 'feather icon-layers', 'warning', 'pass', 'pass', '', ' ' + result.error);
                    } else {
                        notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' ' + result.error);
                    }
                },
                error: function(xhr, resp, text) {
                    notify('top', 'right', 'feather icon-layers', 'danger', 'pass', 'pass', '', ' Server error');
                }
            })
        });
    });
});
