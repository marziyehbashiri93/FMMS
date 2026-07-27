import { AppTabs } from './AppTabs';

export type StatusTabOption<T extends string> = {
  value: T | '';
  label: string;
};

type StatusFilterTabsProps<T extends string> = {
  value: T | '';
  options: ReadonlyArray<StatusTabOption<T>>;
  onChange: (value: T | '') => void;
  ariaLabel?: string;
};

/** Status filter tabs — same visual language as AppTabs (secondary accent). */
export function StatusFilterTabs<T extends string>({
  value,
  options,
  onChange,
  ariaLabel = 'فیلتر وضعیت',
}: StatusFilterTabsProps<T>) {
  return (
    <AppTabs
      value={value}
      onChange={onChange}
      ariaLabel={ariaLabel}
      scrollable
      items={options.map((option) => ({
        value: option.value,
        label: option.label,
      }))}
    />
  );
}
