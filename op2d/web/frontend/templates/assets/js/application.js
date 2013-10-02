// Declare global vars
var settings={};
var selectBox = '';
var timeout = '';
var audio_codecs = {};

// Overrride serialize function to return true/false

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

// overide serialize function
$.fn.serializeObject = function()
{
    var o = {};
    var a = this.serializeArray({ checkboxesAsBools: true });
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


// Capatalize function

String.prototype.capitalize = function(lower) {
    return (lower ? this.toLowerCase() : this).replace(/(?:^|\s)\S/g, function(a) { return a.toUpperCase(); });
};

function notifyError(data) {
    alertify.error("<strong>Error "+ data.responseJSON.msg.split(":")[0] +"</strong>:<br/> "+ data.responseJSON.msg.split(/:(.+)?/)[1]);
}

function getAccountId(){
    var account = $('[id^="account_"] .selected').clone();
    account.find("i").remove();
    account = account.html();
    return account;
}

function removeAccount() {
    var account = getAccountId();

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

function populateRegistration(index, value,reg_counter) {
    var el = $('#account_'+index).find("i");
    el.remove();

    $.getJSON('api/v1/accounts/'+value.id+'/info', function(data1) {
        if (data1.info.registration.state === 'succeeded') {
            $('#account_'+index).append("<i class='pull-right icon-circle text-success'></i>");
        } else if (data1.info.registration.state === 'failed') {
            $('#account_'+index).append("<i class='pull-right icon-circle text-danger'></i>");
        } else if ( data1.info.registration.state === "ended" && value.enabled === true) {
            $('#account_'+index).append("<i class='pull-right icon-circle'></i>");
        } else {
            $('#account_'+index).append("<i class='pull-right icon-circle text-warning'></i>");
            console.log("test "+ reg_counter);
            if (reg_counter !== 1) {
                timeout = setTimeout(function() {
                    reg_counter=1;
                    populateRegistration(index, value, reg_counter);
                },1000);
            } else {
                console.log("here");
                reg_counter=0;
            }
        }
    });
}

function setDefaultAccount() {
    //console.log("add default handler");
    $("[name=nav_account_list]").unbind('change.myEvents').bind('change.myEvents', function() {
        //console.log("c add default handler");
        data = "{\"default_account\": \"" + $("[name=nav_account_list]").val()+"\"}";

        console.log(data);
        var that = this;
        $.ajax({
            type: "PUT",
            url: "api/v1/settings",
            data: data,
            dataType:"json",
            contentType: 'application/json',
            success: function(){
                console.log("Updated dault account" + data );
                $(that).parent().find('.bootstrap-select > button').addClass('btn-success').blur();
                timeout = setTimeout(function() {
                    $(that).parent().find('.bootstrap-select > button').removeClass("btn-success");
                    //$("[name=nav_account_list]").parent().parent().removeClass('has-success');
                },1000);
                $("[name=nav_account_list]").unbind('change.myEvents');
                getSettings();
            },
            error: function(){
                console.log("Error");
                $(that).parent().find('.bootstrap-select > button').addClass('btn-danger');
            }
        });
    });
}

function getAccounts(target_id,form, change, rdata) {
    console.log("Get accounts");

    //console.log(rdata);
    change = typeof change !== 'undefined' ? change : 1;

    var account = getAccountId();

    $.getJSON('api/v1/accounts', function(data) {
        $('#'+target_id).empty().html(
            "<li style='margin-right:4px'>"+
                "<div id='account_buttons' class='btn-group btn-group-xs pull-right'>"+
                    "<button id='add_account' data-toggle='modal' href='#myModal' class='btn btn-primary'><i class='icon-fixed-width icon-plus'></i></button>"+
                    "<button id='remove_account' class='btn btn-default btn-disabled' disabled><i class=' icon-fixed-width icon-minus'></i></button>"+
                "</div>"+
            "</li>"
        );
        console.log(data);

        $("[name=nav_account_list]").empty();

        $.each(data.accounts, function(index,value) {
            $("[name=nav_account_list]").append("<option value=\""+value.id + "\">"+value.id+"</option>");
            $('#'+target_id).prepend("<li><a id=account_"+index+" href='#'>"+value.id+"</a></li>");

            // Get registration state
            populateRegistration(index, value);

            // Add click handler
            $('#account_'+index).click(function (){
                $('.selected').removeClass("selected");
                $('#remove_account').removeClass("btn-disabled").removeAttr("disabled");
                populateRegistration(index, value);
                populateAccountForms(form,value.id, value);
                $(this).addClass("selected");
            });

            //console.log("At "+value.id + "Account "+ account) ;
            console.log("Default account "+settings.default_account);
            if ( value.id === settings.default_account && change === 1) {
                $('[id^="account_"]').removeClass('selected');
                console.log("Populate and select");
                $('#account_'+index).addClass('selected');
                populateAccountForms(form,value.id, value);
            } else if (value.id === account && change === 0) {
                console.log("Populate");
                $('#account_'+index).addClass('selected');
                populateAccountForms(form,value.id, value);
            }
            // console.log(value);
        });

        $("[name=nav_account_list]").unbind('change.myEvents');
        $("[name=nav_account_list]").selectpicker('refresh');
        $("[name=nav_account_list]").selectpicker('val', settings.default_account);
        setDefaultAccount();

        $('#remove_account').click(function () {
            removeAccount();
        });
    });
}

function getSettings() {
    $.getJSON('api/v1/settings', function(data) {
        settings = data;
        getAccounts('account_list','account_info_form');
        populateSpeedDial();
        populateAudioDevices();
        //setDefaultAccount();
    });
    $.getJSON('api/v1/system/audio_codecs', function(data) {
        audio_codecs = data.audio_codecs;
        //getAccounts('account_list','account_info_form');
    });
}

function saveListClick(field,account) {
    var enabled_list = [];
    $("ol#audio_codecs li label input:checked").each(function(){
        enabled_list.push($(this).attr('name'));
    });

    $.ajax({
        type: "PUT",
        url: "api/v1/accounts/"+account,
        data: "{\"rtp\":{\"audio_codec_list\": "+ JSON.stringify(enabled_list) + "}}",
        contentType: 'application/json',
        dataType:"json",
        success: function(){
            $(field).closest('ol').addClass('success');
            //clearTimeout(timeout);
            getAccounts('account_list','account_info_form', 0);
            timeout = setTimeout(function() {
                $(field).closest('ol').removeClass('success');
            },1000);
        },
        error: function(rdata){
            // $(that).closest('.form-group').addClass("has-error");
            console.log("Error");
            $(field).closest('ol').addClass('error');
            $(field).focus();
            notifyError(rdata);
            //return false;
       }
    });
}

function updateField(value,value2,key,key1,account_id) {
    var data = '';
    var key2 = '';
    var value3= '';

    if (key1 === '' && value2 ==='') {
        key2 = key;
        value3 = value;
    } else {
        key2 = key1;
        value3=value2;
    }

    console.log("Finding/Updating "+key + " " +key2);

    if ( key2 === "msrp_relay" && value3 !== null ) {
        temp = String(value3).split(':');
        value3 = temp[0];
        updateField('',temp[1].split(';')[0],'msrp','msrp_port',account_id);
        updateField('',temp[1].split(';')[1].split('=')[1],'msrp','msrp_general_transport',account_id);
    } else if ( key2 === "outbound_proxy" && value3 !== null ) {
        temp = String(value3).split(':');
        value3 = temp[0];
        updateField('',temp[1].split(';')[0],'sip','sip_port',account_id);
        updateField('',temp[1].split(';')[1].split('=')[1],'sip','proxy_transport',account_id);
    } else if ( key2 === "password") {
        for (var i=0; i<Math.ceil(value3.length/2); i++) {
            value3=value3+"*";
        }
    } else if (key === 'message_summary' && key2 === 'enabled') {
        console.log("Exit");
        return;
    }

    $("input[name="+ key2 + "]").val(value3).prop('checked',value3).unbind('change').bind('change', function(e) {
        var that = this;

        if ( key1 === '' && value2 ==='' ) {
            data = JSON.stringify($(this).serializeObject());
        }
        else if ( key2 === 'msrp_relay' || key2 === 'msrp_port'){
            if ($(this).val() !== '' ){
                data = "{\"nat_traversal\": {\"msrp_relay\":\""+$('[name~=msrp_relay]').val()+":"+ $('[name~=msrp_port]').val() +";transport="+$('[name="msrp_general_transport"]').val()+"\"}}";
            } else {
                data = "{\"nat_traversal\": {\"msrp_relay\":\"\"}}";
            }
        }
        else if ( key2 === 'outbound_proxy' || key2 === 'sip_port'){
            if ($(this).val() !== '' ){
                data = "{\"sip\": {\"outbound_proxy\":\""+$('[name~=outbound_proxy]').val()+":"+ $('[name~=sip_port]').val() +";transport="+$('[name="proxy_transport"]').val()+"\"}}";
            } else {
                data = "{\"sip\": {\"outbound_proxy\":\"\"}}";
            }
        }
        else {
            data = "{\""+key+"\": " + JSON.stringify($(this).serializeObject())+"}";
        }

        console.log(data);
        $.ajax({
            type: "PUT",
            url: "api/v1/accounts/"+account_id,
            data: data,
            dataType:"json",
            contentType: 'application/json',
            success: function(rdata) {
                $(that).closest('.form-group').addClass("has-success");
                timeout = setTimeout(function() {
                    $(that).closest('.form-group').removeClass('has-success');
                },2500);
                console.log("Updated " + key +":"+ key2);
                getAccounts('account_list','account_info_form', 0, rdata);
            },
            error: function(rdata){
                $(that).closest('.form-group').addClass("has-error");
                //$(that).focus();
                console.log("Error");
                notifyError(rdata);
                //return false;
            }
        });
        //}
    }).unbind('focus').bind('focus', function() {
        $(this).closest('.form-group').removeClass('has-error');
        $(this).closest('.form-group').removeClass('has-success');
    });

    $("select[name="+key2+"]").unbind('change.myEvents');

    $("select[name="+key2+"]").selectpicker('val',value3).bind('change.myEvents', function() {

        data = "{\""+key+"\": " + JSON.stringify($(this).serializeObject())+"}";

        if ( key2 === 'proxy_transport'){
            //console.log($('[name~=outbound_proxy]').val());
            if ($('[name~=outbound_proxy]').val() !== '' ){
                data = "{\"sip\": {\"outbound_proxy\":\""+$('[name~=outbound_proxy]').val()+":"+ $('[name~=sip_port]').val() +";transport="+$('[name="proxy_transport"]').val()+"\"}}";
            } else {
                return;
            }
        } else if ( key2 === 'msrp_general_transport'){
            if ($('[name~=msrp_relay]').val() !== '' ){
                data = "{\"nat_traversal\": {\"msrp_relay\":\""+$('[name~=msrp_relay]').val()+":"+ $('[name~=msrp_port]').val() +";transport="+$('[name="msrp_general_transport"]').val()+"\"}}";
            } else {
                return;
            }
        }

        console.log(data);
        var that = this;
        $.ajax({
            type: "PUT",
            url: "api/v1/accounts/"+account_id,
            data: data,
            dataType:"json",
            contentType: 'application/json',
            success: function(){
                $("select[name="+key2+"]").parent('div').find('button').addClass("btn-success").blur();
                $("select[name="+key2+"]").parent().parent().addClass('has-success');
                console.log("Updated " + key +":"+ key2);
                timeout = setTimeout(function() {
                    $("select[name="+key2+"]").parent('div').find('button').removeClass("btn-success");
                    $("select[name="+key2+"]").parent().parent().removeClass('has-success');
                },1000);
                getAccounts('account_list','account_info_form', 0);
            },
            error: function(rdata){
                console.log("Error");
                notifyError(rdata);
            }
        });
    });
}

function populateAccountForms(frm, account_id, data) {

    // Show account tabs if account is not bonjour

    if (account_id !== "bonjour@local") {
        $('#account_advanced_tab').show();
        $('#account_server_tab').show();
        $('#account_network_tab').show();
        $("#password").prop('disabled', false);
        $("#password").prop('enabled', true);
        $("#password").closest('.form-group').show();
        $('#remove_account').prop('disabled', false).prop('enabled', true).addClass('btn-disabled');
    } else {
        $('#account_info_tab a').tab('show');
        $('#account_advanced_tab').fadeOut();
        $('#account_server_tab').fadeOut();
        $('#account_network_tab').fadeOut();
        $("#password").prop('disabled', true);
        $("#password").closest('.form-group').hide();
        $('#remove_account').prop('disabled', true).addClass('btn-disabled');
    }

    $("#account_media_form #audio_codecs").empty();

    // Loop data from account

    $.each(data, function(key, value){
        //console.log(key+": "+value);

        if( key === 'rtp') {

            var list=$(value.audio_codec_list).toArray();
            var global_list = $(settings.rtp.audio_codec_list).toArray();

            var available_codecs = $(audio_codecs).toArray();

            if (value.audio_codec_list === null) {
                $.each(settings.rtp.audio_codec_list, function(key,value2) {
                    if ( $.inArray(value2, global_list)  != -1) {
                        $("#account_media_form #audio_codecs").append("<li><div class=\"checkbox smaller smaller-top\">"+
                            "<label>"+
                            "<input name=\""+value2+"\" type=\"checkbox\" checked>"+ value2 +
                            "</label>"+
                            "</div></li>"
                        );
                    } else  {
                        $("#account_media_form #audio_codecs").append("<li><div class=\"checkbox smaller smaller-top\">"+
                            "<label>"+
                            "<input name=\""+value2+"\" type=\"checkbox\">"+ value2 +
                            "</label>"+
                            "</div></li>"
                        );
                    }
                    $("input[name="+ value2 + "]").unbind('change').bind('change', function(){
                        saveListClick(this,account_id);
                    });
                });
            } else {
                $.each(value.audio_codec_list, function(key,value2) {
                    $("#account_media_form #audio_codecs").append("<li><div class=\"checkbox smaller smaller-top\">"+
                        "<label>"+
                        "<input name=\""+value2+"\" type=\"checkbox\" checked>"+ value2 +
                        "</label>"+
                        "</div></li>"
                    );

                    $("input[name="+ value2 + "]").unbind('change').bind('change', function(){
                        saveListClick(this,account_id);
                    });
                });
                 $.each(settings.rtp.audio_codec_list, function(key,value2) {
                        if ( $.inArray(value2, list) === -1) {
                            $("#account_media_form #audio_codecs").append("<li><div class=\"checkbox smaller smaller-top\">"+
                                "<label>"+
                                "<input name=\""+value2+"\" type=\"checkbox\">"+ value2 +
                                "</label>"+
                                "</div></li>"
                            );
                        $("input[name="+ value2 + "]").unbind('change').bind('change', function(){
                            saveListClick(this,account_id);
                        });
                    }
                });

            }

            $("#account_media_form input[name="+ key +"_inband_dtmf]").prop('checked',value.inband_dtmf);

            updateField('',value.srtp_encryption,key,'srtp_encryption',account_id);
        }



        if (key === 'sip' ||
            key === 'nat_traversal' ||
            key === 'display_name' ||
            key === 'enabled' ||
            key === 'auth' ||
            key === 'msrp' ||
            key === 'pstn' ||
            key === 'message_summary' ||
            key === 'xcap') {
            if (key !== 'display_name' && key !== 'enabled') {
                $.each(value, function(key1,value2) {
                    if (key !== 'xcap' && key1 !== 'enabled') {
                        updateField(value,value2,key,key1,account_id);
                    }
                });
            } else {
                updateField(value,'',key,'',account_id);
            }
        }
    });
}

function populateSystemTab() {
    $('#system_info').empty();

    $.getJSON('api/v1/system/info', function(data) {
        $('#system_info').append("<dl class='dl-horizontal' id='system_info_list'></dl>");
        $.each(data.info, function(key,value2) {
            $('#system_info_list').append(
                "<dt>" +
                key.replace("_"," ").capitalize() +
                "</dt><dd>" + value2 +
                "</dd>"
            );
        });
    });
}

function updateSpeedDial(count, name,field) {
    console.log("Finding:"+field+"_"+count);
    $("input[name="+field+"_" +count + "]").val(name).unbind('change').bind('change', function(e) {
            var that = this;

            //if ($("input[name=name_" +count + "]").val() !=='' && $("input[name=uri_" +count + "]").val() !== '') {
                data = "{\"op2\":{ \"speed_dialing\": ";
                data1 = [];
                for (var i=1;i<4;i++) {
                    //if ($("input[name=name_" +i + "]").val() !=='' && $("input[name=uri_" +i + "]").val() !== '') {
                        data1.push($("input[name=name_" + i + "]").val() +"|" + $("input[name=uri_" + i + "]").val());
                    //}
                }
                data = data + JSON.stringify(data1) + '}}' ;
                //console.log(data);
                $.ajax({
                    type: "PUT",
                    url: "api/v1/settings",
                    data: data,
                    contentType: 'application/json',
                    success: function(rdata) {

                        $('#speed_dialing_form div').addClass('has-success');
                        timeout = setTimeout(function() {
                            $('#speed_dialing_form div').removeClass('has-success');
                        },1000);
                        getSettings();
                        console.log("Updated speed dialing" + data );
                    },
                    error: function(rdata){
                        $(that).closest('.form-group').addClass("has-error");
                        //$(that).focus();
                        console.log("Error");
                        notifyError(rdata);
                        //return false;
                    }
                });
            //}
        }).unbind('focus').bind('focus', function() {
            $(this).closest('.form-group').removeClass('has-error');
            $(this).closest('.form-group').removeClass('has-success');
        });
}

function updateAudioSettings(value,value2,key,key2) {
    $("select[name="+key2+"]").unbind('change.myEvents');

    $("select[name="+key2+"]").selectpicker('val',value).bind('change.myEvents', function() {
        data = "{\""+key+"\": " + JSON.stringify($(this).serializeObject())+"}";

        console.log(data);
        var that = this;
        $.ajax({
            type: "PUT",
            url: "api/v1/settings",
            data: data,
            dataType:"json",
            contentType: 'application/json',
            success: function(){
                $("select[name="+key2+"]").parent('div').find('button').addClass("btn-success").blur();
                $("select[name="+key2+"]").parent().parent().addClass('has-success');
                console.log("Updated " + key +":"+ key2);
                timeout = setTimeout(function() {
                    $("select[name="+key2+"]").parent('div').find('button').removeClass("btn-success");
                    $("select[name="+key2+"]").parent().parent().removeClass('has-success');
                },2500);
                getSettings();
                //getAccounts('account_list','account_info_form', 0);
            },
            error: function(rdata){
                console.log("Error");
                notifyError(rdata);
            }
        });
    });
}

function populateSpeedDial() {
    var count = 0;
    for (var i=1;i<4;i++) {
        updateSpeedDial(i, "","name");
        updateSpeedDial(i, "","uri");
    }
    $.each(settings.op2.speed_dialing, function(index,value){
        count++;
        value = value.split('|');
        updateSpeedDial(count, value[0],"name");
        updateSpeedDial(count, value[1],"uri");
    });
}

function populateAudioDevices() {
    $("#input_device").empty();
    $("#output_device").empty();
    $("#alert_device").empty();

    $.getJSON('api/v1/system/audio_devices', function(data) {
        $.each(data.devices, function(key,value2) {
            $.each(value2, function(index,value){
                if (!value) {
                    value='None';
                }
                var text='';
                if (value == "system_default") {
                    text='System Default';
                } else {
                    text=value;
                }

                if (key === 'input') {
                    $('#input_device').append("<option value=\""+value + "\">"+text+"</option>");
                    $('#input_device').unbind('change.myEvents');
                    $('#input_device').selectpicker('refresh');
                } else if (key === 'output') {
                    $('#output_device').append("<option value=\""+value + "\">"+text+"</option>");
                    $('#output_device').unbind('change.myEvents');
                    $('#output_device').selectpicker('refresh');
                    $('#alert_device').append("<option value=\""+value + "\">"+text+"</option>");
                    $('#alert_device').unbind('change.myEvents');
                    $('#alert_device').selectpicker('refresh');
                }
                console.log(value);
            });
        });
        $.each(settings.audio, function(key,value){
            if (!value) {
                value='None';
            }
            updateAudioSettings(value,'','audio',key);
            //updateSpeedDial(count, value[1],"uri");
        });
    });
}

$(document).ready(function() {
    getSettings();

    $('select').selectpicker();

    $('#reregister').click(function(event){
        var account = getAccountId();
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

    $('button[id^="call_"]').click(function(event){

        console.log("call");
        var account = $('[name="nav_account_list"]').val();
        event.preventDefault();
        var that = this ;
        var id_number = this.id.replace(/^[^\d]+/, "");
        //$(that).button('loading').addClass('btn-info');
        //var data = "{\"from\":\""+account+"\", \"to\": \""+ $('#uri_1').val() + "\"}";
        var data = "from="+account+"&to="+ $('#uri_'+id_number).val();
        console.log(data);
        $.ajax({
            type: "get",
            url: "/api/v1/sessions/dial?"+data,
            data: data,
            success: function(){
                //getAccounts('account_list','account_info_form', 0);
                timeout = setTimeout(function() {
                    $(that).button('reset').removeClass('btn-info');
                },500);

            },
            error: function(rdata){
                console.log(rdata);
                console.log("Error");
                notifyError(rdata);
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
            //var order_list =[];
            $("ol#audio_codecs li label input:checked").each(function(){
                enabled_list.push($(this).attr('name'));
            });
            // $("ol#audio_codecs li label input").each(function(){
            //     order_list.push($(this).attr('name'));
            // });
            //
            //console.log(JSON.stringify(enabled_list));
            var account = getAccountId();

            //console.log(account);
            console.log("{\"rtp\":{\"audio_codec_list\": "+ JSON.stringify(enabled_list) + "}}");
            $.ajax({
                type: "PUT",
                url: "api/v1/accounts/"+account,
                data: "{\"rtp\":{\"audio_codec_list\": "+ JSON.stringify(enabled_list) + "}}",
                contentType: 'application/json',
                dataType:"json",
                success: function(){
                    $(that).addClass('success');
                    getAccounts('account_list','account_info_form', 0);
                    timeout = setTimeout(function() {
                        //console.log('Timeout'+$(that));
                        $(that).removeClass('success');
                    },2500);
                },
                error: function(rdata){
                    console.log("Error");
                    notifyError(rdata);
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
            $('.navbar-nav li').removeClass('active');
        } else if ( $(e.target).attr('href') == "#audio_tab" ) {
            //populateAudioCodecs();
            populateAudioDevices();
        }
        //e.relatedTarget // previous tab
    });

    $('#refresh').click(function(event){
        var account = getAccountId();
        event.preventDefault();
        var that = this ;
        $(that).button('loading').addClass('btn-info');
        $.ajax({
            type: "GET",
            url: "api/v1/system/refresh_audio_devices",
            success: function(){
                populateAudioDevices();
                timeout = setTimeout(function() {
                    $(that).button('reset').removeClass('btn-info');
                },400);
            },
            error: function(rdata){
                console.log("Error");
                notifyError(rdata);
                return false;
            }
        });
    });

     $('#account_add_form').on('submit', function(event){
        event.preventDefault();
        var display_name = $(this).find("input[name='display_name1']").val();
        var pass = $(this).find("input[name='password1']").val();
        var id = $(this).find("input[name='id']").val();
        //console.log($(this).find("input[name='id']").val());
        var data = '{"id":"'+ id + '","display_name":"' + display_name + '", "auth":{"password":"'+ pass +'"}}';
        // console.log(data);
        $.ajax({
            type: "POST",
            url: "api/v1/accounts",
            data: data ,
            dataType:"json",
            contentType: 'application/json',
            success: function(){
                $("#myModal").modal('hide');
                getAccounts('account_list','account_info_form');
                return false;
            },
            error: function(rdata){
                console.log("Error");
                notifyError(rdata);
                return false;
            }
        });
        return false;
    });

});
