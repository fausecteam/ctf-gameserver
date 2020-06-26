/* jshint asi: true, sub: true */

'use strict'


$(document).ready(function() {
    $.getJSON('../status.json', {}, buildTable)
})

function buildTable(data) {
    const statusDescriptions = data['status-descriptions']

    // Extract raw DOM element from jQuery object
    const table = $('#status-table')[0]

    // Tick header
    const tick_template = table.querySelectorAll('thead th')[2]
    for (const tick of data['ticks']) {
        const node = tick_template.cloneNode(true)
        node.querySelector('span').textContent = tick
        tick_template.parentNode.insertBefore(node, tick_template)
    }
    tick_template.parentNode.removeChild(tick_template)

    // Do not use jQuery here for performance reasons (we're creating a lot of elements)
    const template = $('#team-template-row')[0]
    for (const team of data['teams']) {
        const entry = template.cloneNode(true)
        entry.setAttribute('id', `team-${team.id}-row`)
        const tds = entry.querySelectorAll('td')
        if (!team.nop) {
            entry.setAttribute('class', '')
        }

        // image
        if (team['image'] === undefined) {
            tds[0].innerHTML = '' // delete all children
        } else {
            tds[0].querySelector('a').setAttribute('href', team['image'])
            const img = tds[0].querySelector('img')
            img.setAttribute('src', team['thumbnail'])
            img.setAttribute('alt', team['name'])
        }

        // Name
        tds[1].querySelector('strong').textContent = team['name']

        // Service status per tick
        for (const statuses of team['ticks']) {
            const col = document.createElement('td')

            for (let i = 0; i < statuses.length; i++) {
                let status = statuses[i]

                const text = document.createTextNode(data['services'][i] + ': ')

                const span = document.createElement('span')
                let statusClass
                if (status === '') {
                    // Not checked
                    status = -1    // For `statusDescriptions`
                    statusClass = 'muted'
                } else {
                    statusClass = statusClasses[status]
                }
                span.setAttribute('class', `text-${statusClass}`)
                span.textContent = statusDescriptions[status]

                col.appendChild(text)
                col.appendChild(span)
                col.appendChild(document.createElement('br'))
            }

            entry.appendChild(col)
        }
        template.parentNode.appendChild(entry)
    }
    template.parentNode.removeChild(template)

    table.hidden = false
}
