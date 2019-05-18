'use strict'


$(document).ready(function() {
    $(window).bind('hashchange', function(e) {
        loadTable()
    })

    loadTable()
})


function loadTable() {

    const serviceSlug = window.location.hash.slice(1)
    if (serviceSlug.length == 0) {
        return
    }

    $.getJSON('service-history.json', {'service': serviceSlug}, buildTable)

}


function buildTable(data) {

    $('#selected-service').text(data['service-name'])

    const statusDescriptions = data['status-descriptions']
    const statusClasses = {
        '0': 'success',
        '1': 'danger',
        '2': 'danger',
        '3': 'warning',
        '4': 'info'
    }

    // Extract raw DOM element from jQuery object
    let table = $('#history-table')[0]

    let tableHeadRow = $('#history-table thead tr')[0]
    while (tableHeadRow.firstChild) {
        tableHeadRow.removeChild(tableHeadRow.firstChild)
    }
    // Leave first column (team names) empty
    tableHeadRow.appendChild(document.createElement('th'))
    for (let i = data['min-tick']; i <= data['max-tick']; i++) {
        let col = document.createElement('th')
        col.textContent = i
        col.classList.add('text-center')
        tableHeadRow.appendChild(col)
    }

    let tableBody = $('#history-table tbody')[0]
    while (tableBody.firstChild) {
        tableBody.removeChild(tableBody.firstChild)
    }

    for (const team of data['teams']) {
        // Do not use jQuery here for performance reasons (we're creating a lot of elements)
        let row = document.createElement('tr')

        let firstCol = document.createElement('td')
        firstCol.textContent = team['name']
        row.appendChild(firstCol)

        for (let i = 0; i < team['checks'].length; i++) {
            const check = team['checks'][i]
            const tick = data['min-tick'] + i

            let col = document.createElement('td')

            if (data['graylog-search-url'] === undefined) {
                col.innerHTML = '&nbsp;'
            } else {
                let link = document.createElement('a')
                link.href = encodeURI(data['graylog-search-url'] + '?rangetype=relative&relative=28800&' +
                                      'q=checker:/' + data['service-slug'] + ':.*/ AND team:' + team['id'] +
                                      ' AND tick:' + tick)
                link.target = '_blank'
                link.innerHTML = '&nbsp;'
                col.appendChild(link)
            }

            col.title = statusDescriptions[check]
            if (check != -1) {
                col.classList.add(statusClasses[check])
            }
            row.appendChild(col)
        }

        tableBody.appendChild(row)
    }

    table.hidden = false

}
