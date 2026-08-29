/* jshint asi: true, sub: true, esversion: 6 */

'use strict'


$(document).ready(function() {
    $.getJSON('../scoreboard.json', {}, buildTable)
})

function buildTable(data) {
    const statusDescriptions = data['status-descriptions']

    $('#tick').text(data['tick'])

    // Extract raw DOM element from jQuery object
    const template = $('#team-template-row')[0]

    // Do not use jQuery here for performance reasons (we're creating a lot of elements)
    for (const team of data['teams']) {
        const entry = template.cloneNode(true)
        entry.setAttribute('id', `team-${team.id}-row`)
        const tds = entry.querySelectorAll('td')

        // Position
        tds[0].querySelector('strong').textContent = `${team.rank}.`

        // Image
        if (team['image'] === undefined) {
            // Delete all children
            tds[1].innerHTML = ''
        } else {
            tds[1].querySelector('a').setAttribute('href', team['image'])
            const img = tds[1].querySelector('img')
            img.setAttribute('src', team['thumbnail'])
            img.setAttribute('alt', team['name'])
        }

        // Name
        tds[2].querySelector('strong').textContent = team['name']

        // Service
        const service_template = tds[3]
        for (const service of team['services']) {
            const service_node = service_template.cloneNode(true)

            service_node.querySelector('.points-offense').textContent = service['offense'].toFixed(2)
            service_node.querySelector('.points-defense').textContent = service['defense'].toFixed(2)
            service_node.querySelector('.points-sla').textContent = service['sla'].toFixed(2)

            // Per-flagstore breakdown (only present for multi-store services)
            const flagstore_breakdown = service_node.querySelector('.flagstores-breakdown')
            const flagstore_template = service_node.querySelector('.flagstore-template')
            service['flagstores'].forEach(function(flagstore, index) {
                const flagstore_node = flagstore_template.cloneNode(true)
                flagstore_node.querySelector('.flagstore-index').textContent = index
                flagstore_node.querySelector('.flagstore-offense').textContent = flagstore['offense'].toFixed(2)
                flagstore_node.querySelector('.flagstore-defense').textContent = flagstore['defense'].toFixed(2)
                flagstore_node.removeAttribute('hidden')
                flagstore_breakdown.appendChild(flagstore_node)
            })
            flagstore_template.parentNode.removeChild(flagstore_template)

            service_node.querySelector('a').href += `#team-${team.id}-row`

            if (service['status'] !== '') {
                const statusSpan = service_node.querySelector('.service-status')
                const statusClass = statusClasses[service['status']]
                statusSpan.setAttribute('class', `text-${statusClass}`)
                statusSpan.textContent = statusDescriptions[service['status']]

                service_node.setAttribute('class', 'table-' + statusClass)
            }

            service_template.parentNode.insertBefore(service_node, service_template)
        }
        service_template.parentNode.removeChild(service_template)

        // Offense
        tds[4].textContent = team['offense'].toFixed(2)
        // Defense
        tds[5].textContent = team['defense'].toFixed(2)
        // SLA
        tds[6].textContent = team['sla'].toFixed(2)
        // Total
        tds[7].querySelector('strong').textContent = team['total'].toFixed(2)

        template.parentNode.appendChild(entry)
        entry.hidden = false
    }
}
