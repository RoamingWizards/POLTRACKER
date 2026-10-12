import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { wrap } from '../test/helpers';
import Privacy from './Privacy';
import Settings from './Settings';
import { parseBlocks } from '../lib/markdown';

describe('Privacy', () => {
  it('Settings links to the policy', () => {
    render(wrap(<Settings />, '/settings'));
    const entry = screen.getByTestId('privacy-entry');
    expect(within(entry).getByRole('link', { name: 'Read the privacy policy' })).toHaveAttribute('href', '/privacy');
    expect(entry).toHaveTextContent('collects no telemetry');
  });

  it('shows PRIVACY.md with its sections, keychain service and contact link', () => {
    render(wrap(<Privacy />, '/privacy'));
    const page = screen.getByTestId('privacy-policy');
    expect(within(page).getByRole('heading', { level: 1, name: 'POLTRACKER Privacy Policy' })).toBeInTheDocument();
    for (const h of ['API keys', 'AI requests', 'Data sources', 'Telemetry and analytics', 'Removing your data', 'Third parties', 'Contact']) {
      expect(within(page).getByRole('heading', { level: 2, name: h })).toBeInTheDocument();
    }
    expect(page).toHaveTextContent('com.roamingwizards.poltracker.ai');
    expect(within(page).getByRole('link', { name: 'https://github.com/RoamingWizards/POLTRACKER/issues' })).toBeInTheDocument();
    expect(page.textContent).not.toMatch(/[#*`<>]{2}|\*\*/); // markdown syntax is rendered, not shown
  });

  it('parses lists, wrapped paragraphs and headings', () => {
    expect(parseBlocks('# T\n\nline one\nline two\n\n- a\n- b\n\n## H')).toEqual([
      { type: 'h1', text: 'T' }, { type: 'p', text: 'line one line two' }, { type: 'ul', items: ['a', 'b'] }, { type: 'h2', text: 'H' },
    ]);
  });
});
