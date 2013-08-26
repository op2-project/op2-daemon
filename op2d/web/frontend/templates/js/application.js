function getAccounts(target_id,form) {
    $.getJSON('api/v1/accounts', function(data) {
        console.log(data);
        $.each(data.accounts, function(index,value) {
            $('#'+target_id).append("<li>test</li>");
            console.log(value);
            console.log("1");
        });
    });
}

function populateForm(frm, data) {
    $.each(data, function(key, value){
        $.each(value, function(key1, value1){
            //console.log(key1+":"+value1);
            if( value1 == "1"){
                //alert(value1);
                $('#'+key1,frm).val(value1).attr('checked', true);
            } else {
                $('#'+key1,frm).val(value1).attr('checked', false);
            }
        });
    });
}

$(document).ready(function() {
    getAccounts('account_list','account_info_form');
});
