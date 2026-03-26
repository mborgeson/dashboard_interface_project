import type { Deal } from '@/types/deal';

const STAGE_FOLDER_MAP: Record<string, string> = {
  dead: '0) Dead Deals',
  initial_review: '1) Initial UW and Review',
  active_review: '2) Active UW and Review',
  under_contract: '3) Deals Under Contract',
  closed: '4) Closed Deals',
  realized: '5) Realized Deals',
};

const SP_VIEW_ID = 'a615663a-1e48-4654-b14d-b462f78e72b6';

/**
 * Returns the SharePoint Deal Folder URL using AllItems.aspx browsable view.
 * Pattern derived from actual SharePoint URL:
 * .../Real%20Estate/Forms/AllItems.aspx?id=/sites/BRCapital-Internal/Real Estate/Deals/{stage}/{dealName}&viewid=...
 */
export function getSharePointDealFolderUrl(deal: Deal): string {
  const stageFolder = STAGE_FOLDER_MAP[deal.stage] ?? '1) Initial UW and Review';
  // Use full deal name with (City, ST) for folder name
  const dealName = deal.propertyName;
  const folderPath = `/sites/BRCapital-Internal/Real Estate/Deals/${stageFolder}/${dealName}`;
  return `https://bandrcapital.sharepoint.com/sites/BRCapital-Internal/Real%20Estate/Forms/AllItems.aspx?id=${encodeURIComponent(folderPath)}&viewid=${SP_VIEW_ID}`;
}

/**
 * Returns the SharePoint UW Model folder URL.
 * We can't link directly to the .xlsb file without the sourcedoc GUID,
 * so this opens the deal folder where the UW Model file lives.
 */
export function getSharePointUWModelUrl(deal: Deal): string {
  // Same as deal folder — user opens folder, finds the UW Model file
  return getSharePointDealFolderUrl(deal);
}

/** @deprecated Use getSharePointDealFolderUrl instead */
export function getSharePointDealUrl(deal: Deal): string {
  return getSharePointDealFolderUrl(deal);
}
