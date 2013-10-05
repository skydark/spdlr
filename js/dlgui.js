(function(){
var toJSON = JSON.stringify;
var is_empty = function(s) {
    return $.trim(s) === "";
};

var df_model = {
    'rules': [],
    'facts': []
};

var _reset = function(){
    // update model
    df_model = {
        'rules': [],
        'facts': []
    };
    // update views
    $('#list-fact').empty();
    $('#list-rule').empty();
};
var _delete_formula = function(type_, idx){
    var $list = $('#list-'+type_);
    $list.children('li').children('button.close').hide();
    // update model
    df_model[type_+"s"].splice(idx, 1);
    // update views
    $list.children('li:eq('+idx+')').animate({
        height: '0px',
        opacity: 0
    }, {
        duration: 800,
        complete: function() {
            $(this).remove();
            $list.children('li').children('button.close').show();
        }
    });
};
var _append_formula = function(type_, formula, value){
    // update model
    var model = df_model[type_+"s"];
    model.push(formula);
    // update views
    var $li = $('<li>').addClass("list-group-item")
        .append(value)
        .append('<button type="button" class="close" aria-hidden="true">&times;</button>')
        .appendTo($('#list-'+type_));
    $li.children('button.close')
       .click(function(){
           var $list = $('#list-'+type_);
           var $li = $(this).closest('li');
           var idx = $list.children('li').index($li);
           _delete_formula(type_, idx);
       });
    MathJax.Hub.Queue(["Typeset", MathJax.Hub, $li[0]]);
};
var _formula_to_latex = function(type_, formula){
    return $.parseJSON(pyobj.formula_to_latex(type_, formula));
};
var _verify_formula = function(type_){
    var input = $('#add-' + type_);
    var formula = input.val();
    var ret;
    if (is_empty(formula)) {
        ret = {"error": true, "value": "Empty formula!"};
    } else {
        ret = _formula_to_latex(type_, formula);
    }
    if (ret.error) {
        input.parent().removeClass('has-success').addClass('has-error');
        input.next(".control-label").text(ret.value);
    } else {
        input.parent().removeClass('has-error').addClass('has-success');
        input.next(".control-label").text('');
        input.val("");
        _append_formula(type_, formula, ret.value);
    }
};

var set_query_result = function(ret) {
    var result_box = $('#query-result');
    if (ret.error) {
        result_box.removeClass().addClass('alert alert-danger').text(ret.value);
    } else {
        result_box.removeClass().addClass('alert alert-info').text(ret.value);
        MathJax.Hub.Queue(["Typeset", MathJax.Hub, result_box[0]]);
    }
};

$('#btn-load').click(function(){
    var ret = $.parseJSON(pyobj.load());
    set_query_result(ret);
    if (ret.error) return;
    _reset();
    $.each(['fact', 'rule'], function(idx, type_){
        $.each(ret.model[type_+"s"], function(idx, val){
            _append_formula(type_, val[0], val[1]);
        });
    });
});
$('#btn-save').click(function(){
    var ret = $.parseJSON(pyobj.save(toJSON(df_model)));
    set_query_result(ret);
});
$('#btn-reset').click(function(){
    _reset();
});
$('#form-add-fact').submit(function(e){
    e.preventDefault();
    _verify_formula("fact");
});
$('#form-add-rule').submit(function(e){
    e.preventDefault();
    _verify_formula("rule");
});
$('#form-query').submit(function(e){
    e.preventDefault();
    var logic = $('#logic').val();
    var question = $('#question').val();
    var formula = $('#formula').val();
    var model = toJSON(df_model);
    var ret;
    if ($.inArray(question, ["credulous_entail", "skeptical_entail"]) !== -1 && is_empty(formula)) {
        ret = {"error": true, "value": "Empty formula!"};
    } else {
        ret = $.parseJSON(pyobj.query(logic, question, formula, model));
    }
    set_query_result(ret);
});
})();
