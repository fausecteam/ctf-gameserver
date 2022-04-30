/* jshint asi: true, sub: true, esversion: 6 */

'use strict'


$(document).ready(function() {

    setupDynamicContent('service-history.json', buildTable)

})


function buildTable(data) {

    $('#selected-service').text(data['service-name'])
    $('#min-tick').val(data['min-tick'])
    $('#max-tick').val(data['max-tick'])

    const statusDescriptions = data['status-descriptions']

    // Extract raw DOM element from jQuery object
    let table = $('#history-table')[0]

    // Over a certain number of columns, do not show every tick number in the table head
    let tickTextEvery = 1
    if (data['max-tick'] - data['min-tick'] > 30) {
        tickTextEvery = 5
    }

    let tableHeadRow = $('#history-table thead tr')[0]
    while (tableHeadRow.firstChild) {
        tableHeadRow.removeChild(tableHeadRow.firstChild)
    }
    // Leave first two columns (team numbers & names) empty
    tableHeadRow.appendChild(document.createElement('th'))
    tableHeadRow.appendChild(document.createElement('th'))
    for (let i = data['min-tick']; i <= data['max-tick']; i++) {
        let col = document.createElement('th')
        if (i % tickTextEvery == 0) {
            col.textContent = i
        }
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
        firstCol.classList.add('text-muted')
        firstCol.textContent = team['net_number']
        row.appendChild(firstCol)

        let secondCol = document.createElement('td')
        secondCol.textContent = team['name']
        row.appendChild(secondCol)

        for (let i = 0; i < team['checks'].length; i++) {
            const check = team['checks'][i]
            const tick = data['min-tick'] + i

            let col = document.createElement('td')

            if (data['graylog-search-url'] === undefined) {
                col.innerHTML = '&nbsp;'
            } else {
                let link = document.createElement('a')
                link.href = encodeURI(data['graylog-search-url'] + '?rangetype=relative&relative=28800&' +
                                      'q=service:' + data['service-slug'] + ' AND team:' + team['net_number'] +
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
