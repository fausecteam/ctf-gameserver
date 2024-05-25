/* jshint asi: true, sub: true, esversion: 6 */

'use strict'


$(document).ready(function() {

    setupDynamicContent('missing-checks.json', buildList)

})


function buildList(data) {

    $('#selected-service').text(data['service-name'])
    $('#min-tick').val(data['min-tick'])
    $('#max-tick').val(data['max-tick'])

    // Extract raw DOM element from jQuery object
    let list = $('#check-list')[0]

    while (list.firstChild) {
        list.removeChild(list.firstChild)
    }

    for (const check of data['checks']) {
        let tickEntry = document.createElement('li')

        let prefix = document.createElement('strong')
        prefix.textContent = 'Tick ' + check['tick'] + ': '
        tickEntry.appendChild(prefix)

        for (let i = 0; i < check['teams'].length; i++) {
            const teamID = check['teams'][i][0]
            const isTimeout = check['teams'][i][1]
            const teamName = data['all-teams'][teamID]['name']
            const teamNetNo = data['all-teams'][teamID]['net-number']

            let teamEntry
            if (data['graylog-search-url'] === undefined) {
                teamEntry = document.createElement('span')
            } else {
                teamEntry = document.createElement('a')
                teamEntry.href = encodeURI(data['graylog-search-url'] +
                                           '?rangetype=relative&relative=28800&' +
                                           'q=service:' + data['service-slug'] + ' AND team:' + teamNetNo +
                                           ' AND tick:' + check['tick'])
                teamEntry.target = '_blank'
                if (isTimeout) {
                    teamEntry.classList.add('text-muted')
                }
            }
            teamEntry.textContent = teamName + ' (' + teamNetNo + ')'
            tickEntry.appendChild(teamEntry)

            if (i != check['teams'].length - 1) {
                let separator = document.createElement('span')
                separator.textContent = ', '
                tickEntry.appendChild(separator)
            }

        }

        list.appendChild(tickEntry)
    }

    list.hidden = false

}
