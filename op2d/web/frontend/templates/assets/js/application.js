function getAccounts(target_id,form) {
    $.getJSON('api/v1/accounts', function(data) {
        console.log(data);
        $.each(data.accounts, function(index,value) {
            $('#'+target_id).prepend("<li><a id=account_"+index+" href='#'>"+value.id+"</a></li>");
            $('#account_'+index).click(function (){
                $('.selected').removeClass("selected");
                $('#remove_account').removeClass("btn-disabled").removeAttr("disabled");
                populateAccountForms(form,value.id);
                $(this).addClass("selected");
            });
            // console.log(value);
        });
    });
}


function populateAccountForms(frm, account_id) {
    // console.log("Trying to fill form"+ frm);

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

    $.getJSON('api/v1/accounts/'+account_id, function(data) {
        console.log(data);

        $("#account_media_form #audio_codecs").empty();
        $.each(data.account, function(key, value){
            //console.log(key+": "+value);

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
                                  "</div></li>");
                        });
                   });
                }

            }

            if( value === true) {
                $("#"+frm+" input[name="+key+"]").val(value).prop('checked',true);
            } else {
                $("#"+frm+" input[name="+key+"]").val(value).prop('checked',false);
            }
        });
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
});
