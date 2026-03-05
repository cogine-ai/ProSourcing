import React from 'react';
import { ChevronRight, Home } from 'lucide-react';
import { PDL } from '../lib/pdl';

const Breadcrumbs = ({ activeTab }) => {
  const tabLabels = {
    market: '首页',
    tasks: '采集任务',
    archives: '选品报告',
    algo: '算法配置',
    settings: '系统管理'
  };

  return (
    <nav className={`flex items-center gap-2 ${PDL.breadcrumb.size} font-semibold ${PDL.breadcrumb.color} uppercase tracking-tight mb-4`}>
      <div className="flex items-center gap-1 hover:text-foreground cursor-pointer transition-colors">
        <Home size={10} />
        <span>ProSourcing</span>
      </div>

      <ChevronRight size={10} className="opacity-40" />

      <div className="flex items-center gap-1 cursor-default">
        <span className={PDL.breadcrumb.activeColor}>{tabLabels[activeTab]}</span>
      </div>
    </nav>
  );
};

export default Breadcrumbs;
