// @vitest-environment jsdom
import { afterEach, describe, expect, test } from 'vitest'
import { cleanup, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { DataTable, type Column } from '../DataTable'

interface Row {
  id: string
  name: string
  score: number | null
}

const rows: Row[] = [
  { id: 'a', name: 'Alpha', score: 2 },
  { id: 'b', name: 'Bravo', score: null },
  { id: 'c', name: 'Charlie', score: 9 },
  { id: 'd', name: 'Delta', score: 5 },
]

const columns: Column<Row>[] = [
  { key: 'name', label: 'Name', align: 'left', render: (r) => r.name, sortValue: (r) => r.name },
  {
    key: 'score',
    label: 'Score',
    align: 'right',
    render: (r) => (r.score === null ? '—' : String(r.score)),
    sortValue: (r) => r.score,
    cellStyle: (r) => ({ backgroundColor: r.score === 9 ? 'rgb(1, 2, 3)' : 'transparent' }),
  },
  { key: 'plain', label: 'Plain', align: 'left', render: () => 'x' },
]

function setup(defaultSort = { key: 'score', dir: 'desc' as const }, sticky = false) {
  return render(
    <DataTable
      rows={rows}
      rowKey={(r) => r.id}
      columns={columns}
      caption="Test table"
      defaultSort={defaultSort}
      stickyFirstColumn={sticky}
    />,
  )
}

const names = () =>
  screen
    .getAllByRole('row')
    .slice(1)
    .map((tr) => within(tr).getAllByRole('cell')[0].textContent)

afterEach(cleanup)

describe('DataTable', () => {
  test('header sort control is a button reachable by keyboard', async () => {
    setup()
    const user = userEvent.setup()
    const btn = screen.getByRole('button', { name: /name/i })
    await user.tab()
    expect(document.activeElement).toBe(btn)
    expect(screen.queryByRole('button', { name: /plain/i })).toBeNull()
  })

  test('active column sets aria-sort; others do not', () => {
    setup()
    const ths = screen.getAllByRole('columnheader')
    expect(ths[1].getAttribute('aria-sort')).toBe('descending')
    expect(ths[0].hasAttribute('aria-sort')).toBe(false)
    expect(ths[2].hasAttribute('aria-sort')).toBe(false)
    expect(ths[0].getAttribute('scope')).toBe('col')
  })

  test('Enter toggles sort direction', async () => {
    setup()
    const user = userEvent.setup()
    const btn = screen.getByRole('button', { name: /score/i })
    btn.focus()
    await user.keyboard('{Enter}')
    expect(screen.getAllByRole('columnheader')[1].getAttribute('aria-sort')).toBe('ascending')
    await user.keyboard('{Enter}')
    expect(screen.getAllByRole('columnheader')[1].getAttribute('aria-sort')).toBe('descending')
  })

  test('nulls sort last in both directions', async () => {
    setup()
    const user = userEvent.setup()
    expect(names()).toEqual(['Charlie', 'Delta', 'Alpha', 'Bravo'])
    await user.click(screen.getByRole('button', { name: /score/i }))
    expect(names()).toEqual(['Alpha', 'Delta', 'Charlie', 'Bravo'])
  })

  test('cellStyle is applied to the cell', () => {
    setup()
    const cell = screen.getByText('9').closest('td')!
    expect(cell.style.backgroundColor).toBe('rgb(1, 2, 3)')
  })

  test('table has a caption', () => {
    setup()
    expect(screen.getByRole('table', { name: 'Test table' })).toBeTruthy()
    expect(document.querySelector('caption')?.textContent).toBe('Test table')
  })

  test('stickyFirstColumn makes first header and cells sticky', () => {
    setup(undefined, true)
    expect(screen.getAllByRole('columnheader')[0].className).toContain('sticky')
    expect(screen.getAllByRole('row')[1].querySelector('td')!.className).toContain('sticky')
  })
})
