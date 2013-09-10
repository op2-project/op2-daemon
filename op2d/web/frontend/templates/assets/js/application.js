$.fn.serializeObject = function()
{
    var o = {};
    var a = this.serializeArray();
    $.each(a, function() {
        if (o[this.name] !== undefined) {
            if (!o[this.name].push) {
                o[this.name] = [o[this.name]];
            }
            o[this.name].push(this.value || '');
        } else {
            o[this.name] = this.value || '';
        }
    });
    return o;
};

String.prototype.capitalize = function(lower) {
    return (lower ? this.toLowerCase() : this).replace(/(?:^|\s)\S/g, function(a) { return a.toUpperCase(); });
};

function removeAccount() {
    console.log($('.selected').html());
    var account=$('.selected').html();
    $.fn.dialog2.helpers.confirm("Are you sure to remove account:<br/><p class='text-center text-danger'><strong>" + account + '</strong></p>', {
        confirm: function() {
            $.ajax({
                type: "DELETE",
                url: "api/v1/accounts/"+ account,
                contentType: 'application/json; charset=UTF-8',
                success: function(){
                    $.fn.dialog2.helpers.alert("The account "+account+" has been removed", {});
                    getAccounts('account_list','account_info_form');
                }
            });
        },
        decline: function() { alert("You said no? Right choice!"); }
    });

    event.preventDefault();
}

function getAccounts(target_id,form) {
    $('#'+target_id).empty().html(
        "<li style='margin-right:4px'>"+
            "<div id='account_buttons' class='btn-group btn-group-xs pull-right'>"+
                "<button id='add_account' data-toggle='modal' href='#myModal' class='btn btn-primary'><i class='icon-fixed-width icon-plus'></i></button>"+
                "<button id='remove_account' class='btn btn-default btn-disabled' disabled><i class=' icon-fixed-width icon-minus'></i></button>"+
            "</div>"+
        "</li>"
    );

    $.getJSON('api/v1/accounts', function(data) {
        console.log(data);
        $.each(data.accounts, function(index,value) {
            $('#'+target_id).prepend("<li><a id=account_"+index+" href='#'>"+value.id+"</a></li>");

            $.getJSON('api/v1/accounts/'+value.id+'/info', function(data1) {
                if (data1.info.registration.state === 'succeeded') {
                    $('#account_'+index).append("<i class='pull-right icon-circle text-success'></i>");
                    console.log("ok");
                    //state = "<span class=\"label label-success pull-right\">Registered</span>";
                } else if (data1.info.registration.state === 'failed') {
                    $('#account_'+index).append("<i class='pull-right icon-circle text-danger'></i>");
                }
                //console.log(data1);
            });

            $('#account_'+index).click(function (){
                $('.selected').removeClass("selected");
                $('#remove_account').removeClass("btn-disabled").removeAttr("disabled");
                populateAccountForms(form,value.id);
                $(this).addClass("selected");
            });
            // console.log(value);
        });
        $('#remove_account').click(function () {
            removeAccount();
        });
    });
}


function populateAccountForms(frm, account_id) {

    // Show account tabs if account is not bonjour

    if (account_id !== "bonjour@local") {
        $('#account_advanced_tab').show();
        $('#account_server_tab').show();
        $('#account_network_tab').show();
    } else {
        $('#account_advanced_tab').fadeOut();
        $('#account_server_tab').fadeOut();
        $('#account_network_tab').fadeOut();
    }

    // Add focusout for password

    $("#"+frm+" #inputPassword1").unbind('focusout');
    $("#"+frm+" #inputPassword1").focusout(function (){
        console.log("test"+JSON.stringify($(this).serializeObject()));
        $.ajax({
            type: "PUT",
            url: "api/v1/accounts/"+account_id,
            data: "{\"auth\":"+JSON.stringify($(this).serializeObject())+"}",
            contentType: 'application/json',
            success: function(){
                console.log("Updated password");
                getAccounts('account_list','account_info_form');
                $("#"+frm+" #inputPassword1").val('');
            },
            error: function(){
                console.log("Error updating password");
                //return false;
            }
        });
    });

    // Get account properties

    $.getJSON('api/v1/accounts/'+account_id, function(data) {
        console.log(data);

        $("#account_media_form #audio_codecs").empty();

        // Loop data

        $.each(data.account, function(key, value){
            console.log(key+": "+value);

            if( key === 'rtp') {
                //console.log("In rtp"+value.audio_codec_list);
                //console.log(value['audio_codec_list']);

                if (value.audio_codec_list === null) {
                    $.getJSON('api/v1/settings', function(data) {
                        $.each(data.rtp.audio_codec_list, function(key,value2) {
                            //console.log(key +" "+ value2);
                            $("#account_media_form #audio_codecs").append("<li><div class=\"checkbox smaller smaller-top\">"+
                                "<label>"+
                                "<input type=\"checkbox\" checked>"+ value2 +
                                "</label>"+
                                "</div></li>"
                            );
                        });
                    });
                }
            }

            // if( value === true) {
            //     $("#"+frm+" input[name="+key+"]").val(value).prop('checked',true);
            // } else {

            $("#"+frm+" input[name="+key+"]").val(value).prop('checked',value).unbind('focusout');
            $("#"+frm+" input[name="+key+"]").val(value).prop('checked',value).focusout(function (){
                console.log("test"+JSON.stringify($(this).serializeObject()));
                $.ajax({
                    type: "PUT",
                    url: "api/v1/accounts/"+account_id,
                    data: JSON.stringify($(this).serializeObject()),
                    contentType: 'application/json',
                    success: function(){
                        console.log("updated");
                    },
                    error: function(){
                        console.log("Error");
                        //return false;
                    }
                });
            });
        });
    });
}

function populateSystemTab() {
    $('#system_info').empty();

    $.getJSON('api/v1/system/info', function(data) {
        $('#system_info').append("<dl class='dl-horizontal' id='system_info_list'></dl>");
        $.each(data.info, function(key,value2) {
            //console.log(key +" "+ value2);
            $('#system_info_list').append("<dt>"+
                        key.replace("_"," ").capitalize() +
                        "</dt><dd>"+ value2 +
                      "</dd>");
        });
        //$('#system_info').append("</dl>");
    });
}

$(document).ready(function() {
    getAccounts('account_list','account_info_form');
    var selectBox = $("select").selectBoxIt();
     $("ol#audio_codecs").sortable({
        change: function( event, ui ) {
            $("#reset_audio_codecs").removeClass("btn-disabled").removeAttr("disabled");
        }
    });


    $('a[data-toggle="tab"]').on('shown.bs.tab', function(e) {
        console.log(e.target); // activated tab
        if ( $(e.target).attr('href') == "#system_tab" ) {
            populateSystemTab();
        } else if ( $(e.target).attr('href') == "#start_tab" ) {
            console.log("start");
            console.log($('.navbar-nav li'));
            $('.navbar-nav li').removeClass('active');
        }
        //e.relatedTarget // previous tab
    });

        // $("#remove_account_dialog").dialog2({
        //     showCloseHandle: false,
        //     removeOnClose: false,
        //     autoOpen: false,
        //     closeOnEscape: false,
        //     closeOnOverlayClick: false
        // });

        // $('#remove_account').click(function(event) {
        //     event.preventDefault();
        //     $("#sample1-dialog").dialog2("open");
        // });

     $('#account_add_form').on('submit', function(){

        //console.log(JSON.stringify($(this).serializeObject()));

        $.ajax({
            type: "POST",
            url: "api/v1/accounts",
            data: JSON.stringify($(this).serializeObject()),
            contentType: 'application/json',
            success: function(){
                $("#myModal").modal('hide');
                getAccounts('account_list','account_info_form');
                return false;
            },
            error: function(){
                console.log("Error");
                return false;
            }
        });
        return false;
    });

});
