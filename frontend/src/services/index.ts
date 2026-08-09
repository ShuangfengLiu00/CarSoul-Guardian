export * from "./agentService";
// 显式再导出以消除 holoData / types / timelineTypes 对以下三个名字的重复导出歧义（TS2308）。
// holoData.ts 是它们的规范定义来源；显式具名导出优先于 `export *` 通配，冲突即消解。
export type { TimelineEvent, AlertItem, PredictionItem } from "./holoData";
export * from "./demoData";
export * from "./digitalTwinService";
export * from "./evolutionService";
export * from "./governanceService";
export * from "./healthService";
export * from "./holoData";
export * from "./knowledgeService";
export * from "./riskService";
export * from "./safetyService";
export * from "./soulService";
export * from "./storyData";
// BC-20：timelineData.ts（TIMELINE_DEMO_DATA 剧本数据）不再从 barrel 导出，
// 避免页面/service 误引用回落到演示数据。仅测试文件可直接 import 该模块。
export * from "./timelineService";
export * from "./timelineTypes";
export * from "./types";
export * from "./userService";
export * from "./vehicleService";
export * from "./worldModelService";
