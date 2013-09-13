// Declare global vars
var settings={};
var selectBox = '';
var timeout = '';


(function ($) {

     $.fn.serialize = function (options) {
         return $.param(this.serializeArray(options));
     };

     $.fn.serializeArray = function (options) {
         var o = $.extend({
         checkboxesAsBools: false
     }, options || {});

     var rselectTextarea = /select|textarea/i;
     var rinput = /text|hidden|password|search/i;

     return this.map(function () {
         return this.elements ? $.makeArray(this.elements) : this;
     })
     .filter(function () {
         return this.name && !this.disabled &&
             (this.checked ||
             (o.checkboxesAsBools && this.type === 'checkbox') ||
             rselectTextarea.test(this.nodeName) ||
             rinput.test(this.type));
         })
         .map(function (i, elem) {
             var val = $(this).val();
             return val == null ?
             null :
             $.isArray(val) ?
             $.map(val, function (val, i) {
                 return { name: elem.name, value: val };
             }) :
             {
                 name: elem.name,
                 value: (o.checkboxesAsBools && this.type === 'checkbox') ? //moar ternaries!
                        (this.checked ? true : false) :
                        val
             };
         }).get();
     };

})(jQuery);

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
    var account = $('.selected').clone();
    account.find("i").remove();
    account = account.html();

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
        decline: function() {}
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

function getSettings() {
    $.getJSON('api/v1/settings', function(data) {
        settings = data;
        getAccounts('account_list','account_info_form');
    });
}

function populateAccountForms(frm, account_id) {

    // Show account tabs if account is not bonjour

    if (account_id !== "bonjour@local") {
        $('#account_advanced_tab').show();
        $('#account_server_tab').show();
        $('#account_network_tab').show();
    } else {
        $('#account_info_tab a').tab('show');
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
            $('#system_info_list').append(
                "<dt>" +
                key.replace("_"," ").capitalize() +
                "</dt><dd>" + value2 +
                "</dd>"
            );
        });
    });
}

function populateAudioCodecs() {
    var global_list = $(settings.rtp.audio_codec_list).toArray();

    $("#audio_codecs_general").empty();

    $.each(settings.rtp.audio_codec_order, function(key,value2) {
        var check="";
        if ( $.inArray(value2, global_list) != -1) {
            check="checked";
        }
        $("#audio_codecs_general").append("<li><div class=\"checkbox smaller smaller-top\">"+
                "<label>"+
                "<input name=\""+value2+"\" type=\"checkbox\"" + check +">"+ value2 +
                "</label>"+
                "</div></li>"
        );
    });
}

$(document).ready(function() {
    getSettings();

    $('select').selectpicker();

    $('#reregister').click(function(event){
        var account = $('.selected').clone();
        account.find("i").remove();
        account = account.html();
        event.preventDefault();
        var that = this ;
        $(that).button('loading').addClass('btn-info');
        $.ajax({
            type: "GET",
            url: "api/v1/accounts/"+account+"/reregister",
            success: function(){
                getAccounts('account_list','account_info_form', 0);
                timeout = setTimeout(function() {
                    $(that).button('reset').removeClass('btn-info');
                },500);

            }
        });
    });

    $("ol#audio_codecs").sortable({
        change: function( event, ui ) {
            $("#reset_audio_codecs").removeClass("btn-disabled").removeAttr("disabled");
        },
        stop: function( event, ui ) {
            var that = this;
            var enabled_list = [];
            var order_list =[];
            $("ol#audio_codecs li label input:checked").each(function(){
                enabled_list.push($(this).attr('name'));
            });
            $("ol#audio_codecs li label input").each(function(){
                order_list.push($(this).attr('name'));
            });
            console.log(JSON.stringify(enabled_list));
            var account = $('.selected').clone();
            account.find("i").remove();
            account = account.html();
            console.log("{\"rtp\":{\"audio_codec_list\": "+ JSON.stringify(enabled_list) + "}}");
            $.ajax({
                type: "PUT",
                url: "api/v1/accounts/"+account,
                data: "{\"rtp\":{\"audio_codec_list\": "+ JSON.stringify(enabled_list) + "}}",
                contentType: 'application/json',
                success: function(){
                    console.log($(that).addClass('success'));
                    // console.log($(this).closest('.form-group'));
                    // $(that).closest('.form-group').addClass("has-success");
                    // console.log("Updated " + key);
                    timeout = setTimeout(function() {
                        console.log('Timeout'+$(that));
                        $(that).removeClass('success');
                    },2500);
                },
                error: function(){
                    // $(that).closest('.form-group').addClass("has-error");
                    console.log("Error");
                    $(that).addClass('error');
                    //return false;
               }
            });
            $.ajax({
                type: "PUT",
                url: "api/v1/accounts/"+account,
                data: "{\"rtp\":{\"audio_codec_order\": "+ JSON.stringify(order_list) + "}}",
                contentType: 'application/json',
                success: function(){
                    // console.log($(this).closest('.form-group'));
                    // $(that).closest('.form-group').addClass("has-success");
                    // console.log("Updated " + key);
                },
                error: function(){
                    // $(that).closest('.form-group').addClass("has-error");
                    console.log("Error");
                    $(that).addClass('error');
                    //return false;
               }
            });

        }
    });


    $("ol#audio_codecs_general").sortable();

    $('a[data-toggle="tab"]').on('shown.bs.tab', function(e) {
        console.log(e.target); // activated tab
        if ( $(e.target).attr('href') == "#system_tab" ) {
            populateSystemTab();
        } else if ( $(e.target).attr('href') == "#start_tab" ) {
            console.log("start");
            console.log($('.navbar-nav li'));
            $('.navbar-nav li').removeClass('active');
        } else if ( $(e.target).attr('href') == "#audio_tab" ) {
            populateAudioCodecs();
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
