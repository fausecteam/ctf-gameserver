/* jshint asi: true, sub: true, esversion: 11 */

'use strict'


// Font Awesome icons for the values from `StatusCheck.STATUSES`, '' means "not checked"
const statusIcons = {
    0: 'fa-circle-check',
    1: 'fa-circle-xmark',
    2: 'fa-bug',
    3: 'fa-flag',
    4: 'fa-rotate',
    '': 'fa-circle-question'
}

const numberFormat = new Intl.NumberFormat('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})


$(document).ready(function() {
    $.getJSON('../scoreboard.json', {}, buildScoreboard)
})

function buildScoreboard(data) {
    $('#tick').text(data['tick'])

    const table = $('#scoreboard')[0]
    // NaN if not logged in
    const ownTeamId = parseInt(table.dataset.ownTeam)
    const templates = {
        serviceHead: getTemplate('sb-service-head-template'),
        firstBlood: getTemplate('sb-first-blood-template'),
        teamRow: getTemplate('sb-team-row-template'),
        serviceCell: getTemplate('sb-service-cell-template')
    }

    const lowLlmFilter = document.getElementById('sb-low-llm-filter')
    if (data['teams'].some(team => team['low-llm'])) {
        lowLlmFilter.closest('.form-check').hidden = false
    } else {
        // The browser may have restored a checked state from an earlier visit, which must not apply when the
        // checkbox is hidden
        lowLlmFilter.checked = false
    }
    lowLlmFilter.addEventListener('change', function() {
        buildTableContent(table, data, ownTeamId, templates, lowLlmFilter.checked)
    })
    // Uses `checked` instead of a fixed value to respect a state restored by the browser on reload
    buildTableContent(table, data, ownTeamId, templates, lowLlmFilter.checked)

    // A single delegated instance instead of one per element, because there are thousands of tooltips
    new bootstrap.Tooltip(table, {selector: '[data-bs-toggle="tooltip"]'})

    table.hidden = false
}

function getTemplate(id) {
    return document.getElementById(id).content.firstElementChild
}

// (Re-)Builds everything that depends on the low-LLM filter
function buildTableContent(table, data, ownTeamId, templates, lowLlmOnly) {
    buildServiceHeads(table, data['services'], templates, lowLlmOnly)
    buildTeamRows(table, data, ownTeamId, templates, lowLlmOnly)
}

function buildServiceHeads(table, services, templates, lowLlmOnly) {
    table.querySelectorAll('thead .sb-col-service').forEach(head => head.remove())
    const totalHead = table.querySelector('thead .sb-col-total')
    const scope = lowLlmOnly ? ' among low-LLM teams' : ''

    for (const service of services) {
        const head = templates.serviceHead.cloneNode(true)
        head.querySelector('.sb-service-name').textContent = service['name']

        service['first-bloods'].forEach(function(overallFirstBlood, flagstore) {
            const firstBlood = lowLlmOnly ? service['low-llm-first-bloods'][flagstore] : overallFirstBlood
            const line = templates.firstBlood.cloneNode(true)

            let storeLabel = service['name']
            if (service['flagstores'] > 1) {
                line.querySelector('.sb-first-blood-store').textContent = `#${flagstore}`
                storeLabel = `Flag store #${flagstore} of ${service['name']}`
            }

            const teamSpan = line.querySelector('.sb-first-blood-team')
            let title
            if (firstBlood === null) {
                line.classList.add('sb-first-blood-none')
                teamSpan.textContent = 'no first blood yet'
                title = `${storeLabel}: no first blood${scope} yet`
            } else {
                teamSpan.textContent = firstBlood['name']
                title = `${storeLabel}: first blood${scope} by ${firstBlood['name']} ` +
                        `in tick ${firstBlood['tick']}`
            }

            // Like the original ranks, show the overall first blood struck through, but only if it differs
            if (lowLlmOnly && overallFirstBlood !== null && overallFirstBlood['id'] !== firstBlood?.['id']) {
                const original = line.querySelector('.sb-first-blood-original')
                original.textContent = overallFirstBlood['name']
                original.hidden = false
                title += ` (overall: ${overallFirstBlood['name']} in tick ${overallFirstBlood['tick']})`
            }

            line.dataset.bsTitle = title
            head.appendChild(line)
        })

        totalHead.parentNode.insertBefore(head, totalHead)
    }
}

function buildTeamRows(table, data, ownTeamId, templates, lowLlmOnly) {
    // Do not use jQuery here for performance reasons (we're creating a lot of elements)
    const rows = document.createDocumentFragment()
    let previousTotal = null
    let filteredRank = 0
    for (const team of data['teams']) {
        if (lowLlmOnly && !team['low-llm']) {
            continue
        }
        filteredRank++
        rows.appendChild(buildTeamRow(team, lowLlmOnly ? filteredRank : null, previousTotal, ownTeamId, data,
                                      templates))
        previousTotal = team['total']
    }
    table.querySelector('tbody').replaceChildren(rows)
}

function buildTeamRow(team, filteredRank, previousTotal, ownTeamId, data, templates) {
    const row = templates.teamRow.cloneNode(true)
    row.id = `team-${team['id']}-row`

    // Rank, recalculated when filtered
    const displayRank = filteredRank ?? team['rank']
    const rank = row.querySelector('.sb-rank')
    if (displayRank <= 3) {
        row.classList.add(`sb-podium-${displayRank}`)
        rank.appendChild(createIcon(displayRank === 1 ? 'fa-trophy' : 'fa-medal'))
        rank.setAttribute('aria-label', displayRank)
    } else {
        rank.textContent = displayRank
    }
    if (filteredRank !== null) {
        const originalRank = row.querySelector('.sb-rank-original')
        originalRank.textContent = `#${team['rank']}`
        originalRank.hidden = false
    }

    // Image and name
    fillTeamImage(row.querySelector('.sb-team-image'), team)
    row.querySelector('.sb-team-name').textContent = team['name']
    if (team['id'] === ownTeamId) {
        row.querySelector('.sb-you').hidden = false
    }
    if (team['low-llm']) {
        row.querySelector('.sb-low-llm').hidden = false
    }

    // Services, with the first bloods matching the displayed ones
    const firstBloodsKey = filteredRank === null ? 'first-bloods' : 'low-llm-first-bloods'
    const totalCell = row.querySelector('.sb-col-total')
    team['services'].forEach(function(service, index) {
        const cell = templates.serviceCell.cloneNode(true)
        fillServiceCell(cell, service, data['services'][index][firstBloodsKey], team['id'],
                        data['status-descriptions'])
        row.insertBefore(cell, totalCell)
    })

    // Total
    setNumber(totalCell.querySelector('.sb-total'), team['total'])
    if (previousTotal !== null) {
        // Use a real minus sign (U+2212) instead of a hyphen
        totalCell.querySelector('.sb-gap').textContent = '−' +
                                                         numberFormat.format(previousTotal - team['total'])
    }
    fillComposition(totalCell.querySelector('.sb-composition'), team)

    return row
}

function fillTeamImage(box, team) {
    const link = box.querySelector('a')
    const initials = box.querySelector('.sb-initials')

    if (team['image'] === undefined) {
        link.remove()
        initials.textContent = getInitials(team['name'])
        // Setting style properties through the DOM is allowed by our Content Security Policy, in contrast
        // to inline "style" attributes
        initials.style.backgroundColor = `hsl(${getHue(team['name'])} 45% 52%)`
        initials.hidden = false
    } else {
        link.href = team['image']
        const img = link.querySelector('img')
        img.src = team['thumbnail']
        img.alt = team['name']
        initials.remove()
    }
}

function fillServiceCell(cell, service, firstBloods, teamId, statusDescriptions) {
    // Status
    const status = service['status']
    const pill = cell.querySelector('.sb-pill')
    pill.href += `#team-${teamId}-row`
    pill.classList.add(status === '' ? 'sb-status-none' : `sb-status-${status}`)
    pill.querySelector('i').classList.add(statusIcons[status])
    pill.querySelector('.sb-pill-label').textContent = statusDescriptions[status === '' ? -1 : status]

    // Service total, with per-flagstore breakdown in a tooltip for multi-store services
    const serviceTotal = cell.querySelector('.sb-service-total')
    const serviceSum = service['offense'] + service['defense'] + service['sla']
    setNumber(serviceTotal.querySelector('.sb-value'), serviceSum)
    if (service['flagstores'].length > 0) {
        serviceTotal.classList.add('sb-multi-store')
        serviceTotal.querySelector('.sb-stores-icon').hidden = false
        serviceTotal.dataset.bsToggle = 'tooltip'
        // HTML is safe here because the tooltip only contains formatted numbers
        serviceTotal.dataset.bsHtml = 'true'
        serviceTotal.dataset.bsTitle = buildFlagstoreTooltip(service['flagstores'])
    }

    // Breakdown
    setNumber(cell.querySelector('.sb-offense'), service['offense'])
    setNumber(cell.querySelector('.sb-defense'), service['defense'])
    setNumber(cell.querySelector('.sb-sla'), service['sla'])

    const isFirstBlood = firstBloods.some(function(firstBlood) {
        return firstBlood !== null && firstBlood['id'] === teamId
    })
    if (isFirstBlood) {
        cell.querySelector('.sb-first-blood-mark').hidden = false
    }
}

function buildFlagstoreTooltip(flagstores) {
    // Only use elements allowed by Bootstrap's tooltip sanitizer (e.g. no tables)
    const entries = flagstores.map(function(flagstore, index) {
        return `<span class="sb-store-label">Store #${index}</span>` +
               `<span><i class="fa-solid fa-fire"></i> ${numberFormat.format(flagstore['offense'])}</span>` +
               `<span><i class="fa-solid fa-shield"></i> ${numberFormat.format(flagstore['defense'])}</span>`
    })

    return `<div class="sb-store-grid">${entries.join('')}</div>`
}

function fillComposition(bar, team) {
    // Defense is usually negative, so use absolute values for the shares
    const parts = [team['offense'], team['defense'], team['sla']].map(Math.abs)
    const sum = parts.reduce((a, b) => a + b, 0) || 1

    bar.querySelectorAll('span').forEach(function(segment, index) {
        segment.style.width = `${parts[index] / sum * 100}%`
    })
    bar.dataset.bsTitle = `Offense ${numberFormat.format(team['offense'])} · ` +
                          `Defense ${numberFormat.format(team['defense'])} · ` +
                          `SLA ${numberFormat.format(team['sla'])}`
}

function setNumber(node, value) {
    node.textContent = numberFormat.format(value)
    if (value < 0) {
        node.classList.add('sb-negative')
    }
}

function createIcon(name) {
    const icon = document.createElement('i')
    icon.className = `fa-solid ${name}`
    return icon
}

function getInitials(name) {
    const words = name.split(/\s+/).filter(word => /\w/.test(word))
    if (words.length > 1) {
        return (Array.from(words[0])[0] + Array.from(words[1])[0]).toUpperCase()
    }
    return Array.from(name).slice(0, 2).join('').toUpperCase()
}

// Stable color per team name, so that teams without images stay recognizable
function getHue(name) {
    let hash = 0
    for (const char of name) {
        hash = (hash * 31 + char.codePointAt(0)) | 0
    }
    return Math.abs(hash) % 360
}
