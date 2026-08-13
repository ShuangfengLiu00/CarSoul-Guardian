import { useEffect, useState } from "react";
import {
  Card,
  Tabs,
  Table,
  List,
  Tag,
  Space,
  Input,
  Button,
  Descriptions,
  Alert as AntAlert,
  Statistic,
  Row,
  Col,
  Typography,
  message,
} from "antd";
import type { TableColumnsType } from "antd";
import {
  EnvironmentOutlined,
  SearchOutlined,
  CompassOutlined,
  CarryOutOutlined,
  ReloadOutlined,
} from "@ant-design/icons";
import { mapService } from "@/services/mapService";
import type { MapPoi, MapRoute, MapRegeo } from "@/services/mapService";
import { vehicleService } from "@/services/vehicleService";
import type { Trip } from "@/services/types";
import { useCurrentVehicle } from "@/hooks/useCurrentVehicle";

const { Title, Text } = Typography;

function SourceTag({ source }: { source?: string }) {
  if (source === "live") {
    return <Tag color="green">实时数据</Tag>;
  }
  return <Tag color="orange">数据源未就绪（诚实降级）</Tag>;
}

export default function TravelMap() {
  const { vehicle } = useCurrentVehicle();
  const vehicleId = vehicle?.id;

  const [keyword, setKeyword] = useState("充电站");
  const [region, setRegion] = useState("北京市");
  const [pois, setPois] = useState<MapPoi[]>([]);
  const [poiSource, setPoiSource] = useState<string | undefined>();
  const [loadingPoi, setLoadingPoi] = useState(false);

  const [fromLoc, setFromLoc] = useState("39.908823,116.397470");
  const [toLoc, setToLoc] = useState("39.865237,116.378903");
  const [route, setRoute] = useState<MapRoute | undefined>();
  const [routeSource, setRouteSource] = useState<string | undefined>();

  const [regeoLoc, setRegeoLoc] = useState("39.908823,116.397470");
  const [regeo, setRegeo] = useState<MapRegeo | undefined>();
  const [regeoSource, setRegeoSource] = useState<string | undefined>();

  const [trips, setTrips] = useState<Trip[]>([]);

  const searchPoi = async () => {
    setLoadingPoi(true);
    try {
      const res = await mapService.searchPoi(keyword, region);
      setPoiSource(res?.source);
      setPois(res?.data ?? []);
    } catch {
      setPoiSource("unavailable");
      setPois([]);
    } finally {
      setLoadingPoi(false);
    }
  };

  const calcRoute = async () => {
    try {
      const res = await mapService.route(fromLoc, toLoc);
      setRouteSource(res?.source);
      setRoute(res?.data);
    } catch {
      setRouteSource("unavailable");
    }
  };

  const calcRegeo = async () => {
    try {
      const res = await mapService.regeo(regeoLoc);
      setRegeoSource(res?.source);
      setRegeo(res?.data);
    } catch {
      setRegeoSource("unavailable");
    }
  };

  useEffect(() => {
    searchPoi();
    if (vehicleId) {
      vehicleService.listTrips(vehicleId, 10).then((r) => setTrips(r?.items ?? [])).catch(() => setTrips([]));
    }
  }, [vehicleId]);

  const poiColumns: TableColumnsType<MapPoi> = [
    { title: "名称", dataIndex: "name", key: "name" },
    { title: "地址", dataIndex: "address", key: "address", ellipsis: true },
    { title: "分类", dataIndex: "category", key: "category", width: 180 },
    { title: "坐标", dataIndex: "location", key: "location", width: 190 },
  ];

  return (
    <div style={{ padding: 24, maxWidth: 1280, margin: "0 auto" }}>
      <Title level={3}>
        <CompassOutlined style={{ marginRight: 8, color: "#2563EB" }} />
        出行地图
      </Title>
      <Text type="secondary">充电站 / 路线规划 / 位置解析 —— 腾讯地图能力（经世界模型引擎）</Text>

      {poiSource === "unavailable" && (
        <AntAlert
          style={{ marginTop: 16 }}
          type="warning"
          showIcon
          message="地图服务当前不可用（未配置腾讯地图 key 或接口异常）"
          description="页面展示的是诚实降级状态，配置 TENCENT_MAP_KEY 后即恢复实时数据。"
        />
      )}

      <Tabs
        style={{ marginTop: 16 }}
        items={[
          {
            key: "poi",
            label: (
              <Space>
                <EnvironmentOutlined />
                充电站 / POI 搜索
              </Space>
            ),
            children: (
              <Card>
                <Space wrap style={{ marginBottom: 16 }}>
                  <Input
                    style={{ width: 200 }}
                    value={keyword}
                    onChange={(e) => setKeyword(e.target.value)}
                    placeholder="关键词，如 充电站"
                  />
                  <Input
                    style={{ width: 180 }}
                    value={region}
                    onChange={(e) => setRegion(e.target.value)}
                    placeholder="区域，如 北京市"
                  />
                  <Button type="primary" icon={<SearchOutlined />} onClick={searchPoi} loading={loadingPoi}>
                    搜索
                  </Button>
                </Space>
                <Space style={{ marginBottom: 12 }}>
                  <SourceTag source={poiSource} />
                  <Text type="secondary">{pois.length} 个结果</Text>
                </Space>
                <Table
                  rowKey="poi_id"
                  columns={poiColumns}
                  dataSource={pois}
                  size="small"
                  pagination={{ pageSize: 8 }}
                  locale={{ emptyText: poiSource === "live" ? "无结果" : "地图服务未就绪，暂无数据" }}
                />
              </Card>
            ),
          },
          {
            key: "route",
            label: (
              <Space>
                <CarryOutOutlined />
                驾车路线
              </Space>
            ),
            children: (
              <Card>
                <Space wrap style={{ marginBottom: 16 }}>
                  <Input style={{ width: 220 }} value={fromLoc} onChange={(e) => setFromLoc(e.target.value)} placeholder="起点 lat,lng" />
                  <Input style={{ width: 220 }} value={toLoc} onChange={(e) => setToLoc(e.target.value)} placeholder="终点 lat,lng" />
                  <Button type="primary" onClick={calcRoute}>规划路线</Button>
                </Space>
                <SourceTag source={routeSource} />
                {route && (
                  <Row gutter={16} style={{ marginTop: 16 }}>
                    <Col span={8}><Statistic title="距离" value={(route.distance_m / 1000).toFixed(1)} suffix="km" /></Col>
                    <Col span={8}><Statistic title="预计时长" value={Math.round(route.duration_s / 60)} suffix="min" /></Col>
                    <Col span={8}><Statistic title="途经点" value={route.steps} suffix="个" /></Col>
                  </Row>
                )}
              </Card>
            ),
          },
          {
            key: "regeo",
            label: (
              <Space>
                <CompassOutlined />
                逆地理编码
              </Space>
            ),
            children: (
              <Card>
                <Space wrap style={{ marginBottom: 16 }}>
                  <Input style={{ width: 260 }} value={regeoLoc} onChange={(e) => setRegeoLoc(e.target.value)} placeholder="坐标 lat,lng" />
                  <Button type="primary" onClick={calcRegeo}>解析地址</Button>
                </Space>
                <SourceTag source={regeoSource} />
                {regeo && (
                  <Descriptions column={1} size="small" style={{ marginTop: 12 }}>
                    <Descriptions.Item label="地址">{regeo.formatted_address}</Descriptions.Item>
                    <Descriptions.Item label="省市区">{`${regeo.province} ${regeo.city} ${regeo.district}`}</Descriptions.Item>
                    <Descriptions.Item label="街道">{regeo.street}</Descriptions.Item>
                  </Descriptions>
                )}
              </Card>
            ),
          },
          {
            key: "trips",
            label: (
              <Space>
                <CarryOutOutlined />
                出行记录
              </Space>
            ),
            children: (
              <Card>
                {trips.length === 0 ? (
                  <AntAlert type="info" showIcon message="暂无出行记录（可经 AI 助手规划后产生）" />
                ) : (
                  <List
                    size="small"
                    dataSource={trips}
                    renderItem={(t: Trip, idx) => {
                      const start = (t.start_location as Record<string, unknown> | undefined)?.title
                        ?? (t.start_location as Record<string, unknown> | undefined)?.name
                        ?? "";
                      return (
                        <List.Item>
                          <Space>
                            <Text strong>#{idx + 1}</Text>
                            <Text>{String(start || "-")}</Text>
                            <Tag color="blue">{t.distance} km</Tag>
                            <Text type="secondary">{t.start_time}</Text>
                          </Space>
                        </List.Item>
                      );
                    }}
                  />
                )}
              </Card>
            ),
          },
        ]}
      />
    </div>
  );
}
