// app/src/components/dashboard/segments/TabNavigation.tsx
import clsx from 'clsx';

type TabId = 'discover' | 'investigate' | 'compare';

interface TabNavigationProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
  disabledTabs?: TabId[];
}

const TABS: { id: TabId; label: string; icon: string }[] = [
  { id: 'discover', label: 'Discover', icon: '🔍' },
  { id: 'investigate', label: 'Investigate', icon: '🧭' },
  { id: 'compare', label: 'Compare', icon: '⚖️' },
];

export default function TabNavigation({ activeTab, onTabChange, disabledTabs = [] }: TabNavigationProps) {
  return (
    <div className="flex space-x-1 bg-muted p-1 rounded-lg">
      {TABS.map((tab) => {
        const isDisabled = disabledTabs.includes(tab.id);
        return (
          <button
            key={tab.id}
            onClick={() => !isDisabled && onTabChange(tab.id)}
            disabled={isDisabled}
            className={clsx(
              'flex-1 px-4 py-2 text-sm font-medium rounded-md transition-all flex items-center justify-center gap-2',
              activeTab === tab.id && 'bg-background text-foreground shadow-sm',
              activeTab !== tab.id && !isDisabled && 'text-muted-foreground hover:text-foreground',
              isDisabled && 'opacity-50 cursor-not-allowed'
            )}
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        );
      })}
    </div>
  );
}
