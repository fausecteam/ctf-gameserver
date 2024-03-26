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

            const spans = service_node.querySelectorAll('span')
            const as = service_node.querySelectorAll('a')
            spans[2].textContent = service['offense'].toFixed(2)
            spans[5].textContent = service['defense'].toFixed(2)
            spans[8].textContent = service['sla'].toFixed(2)

            as[1].href += `#team-${team.id}-row`

            if (service['status'] !== '') {
                console.log(service)
                console.log(service['flagstores'])
                // TODO move up
                const flagstore_classes = new Map();
                flagstore_classes.set(-1, 'glyphicon glyphicon-question-sign text-muted'); // NOT_CHECKED
                flagstore_classes.set(0, 'glyphicon glyphicon-ok-sign text-success'); // OK
                flagstore_classes.set(1, 'glyphicon glyphicon-minus-sign text-danger'); // DOWN
                flagstore_classes.set(2, 'glyphicon glyphicon-exclamation-sign text-danger'); // FAULTY
                flagstore_classes.set(3, 'glyphicon glyphicon-question-sign text-warning'); // FLAG_NOT_FOUND
                flagstore_classes.set(4, 'glyphicon glyphicon-plus-sign text-info'); // RECOVERING

                var flagstore_id = 1;
                for (const flagstore of service['flagstores']) {
                    const fs_box = as[0].cloneNode(true)
                    fs_box.firstElementChild.setAttribute('class', flagstore_classes.get(flagstore[0]))
                    fs_box.setAttribute('title', `Flagstore ${flagstore_id}`)
                    fs_box.setAttribute('data-content', flagstore[1] === '' ? 'up' : flagstore[1])
                    spans[9].appendChild(fs_box)
                    flagstore_id++
                }
                spans[9].removeChild(as[0])

                const statusClass = statusClasses[service['status']]
                spans[11].setAttribute('class', `text-${statusClass}`)
                spans[11].textContent = statusDescriptions[service['status']]

                service_node.setAttribute('class', statusClass)
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

    setTimeout(function () {
        //$('[data-toggle="tooltip"]').tooltip()
        $('[data-toggle="popover"]').popover()
    }, 1000)
}
