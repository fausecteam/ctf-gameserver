/* jshint asi: true, sub: true, esversion: 6 */

'use strict'


const statusClasses = {
    0: 'success',
    1: 'danger',
    2: 'danger',
    3: 'warning',
    4: 'info',
    5: 'active'
}


function setupDynamicContent(jsonPath, buildFunc) {

    function load(_) {
        loadDynamicContent(jsonPath, buildFunc)
    }

    $(window).bind('hashchange', load)
    $('#min-tick').change(load)
    $('#max-tick').change(load)
    $('#refresh').click(load)
    $('#load-current').click(function(_) {
        // Even though the current tick is contained in the JSON data, it might be outdated, so load the
        // table without a "to-tick"
        loadDynamicContent(jsonPath, buildFunc, true)
    })

    loadDynamicContent(jsonPath, buildFunc)

}


function loadDynamicContent(jsonPath, buildFunc, ignoreMaxTick=false) {

    makeFieldsEditable(false)
    $('#load-spinner').attr('hidden', false)

    const serviceSlug = window.location.hash.slice(1)
    if (serviceSlug.length == 0) {
        $('#load-spinner').attr('hidden', true)
        makeFieldsEditable(true)
        return
    }

    const fromTick = parseInt($('#min-tick').val())
    const toTick = parseInt($('#max-tick').val()) + 1
    if (isNaN(fromTick) || isNaN(toTick)) {
        return
    }

    let params = {'service': serviceSlug, 'from-tick': fromTick}
    if (!ignoreMaxTick) {
        params['to-tick'] = toTick
    }
    $.getJSON(jsonPath, params, function(data) {
        buildFunc(data)
        $('#load-spinner').attr('hidden', true)
        makeFieldsEditable(true)
    })

}


function makeFieldsEditable(writeable) {

    $('#service-selector').attr('disabled', !writeable)
    $('#min-tick').attr('readonly', !writeable)
    $('#max-tick').attr('readonly', !writeable)
    $('#refresh').attr('disabled', !writeable)
    $('#load-current').attr('disabled', !writeable)

}
