// 仪表盘核心指标由前端 Pinia Store 从资产列表数据计算而得。
// 此处作为占位模块，便于后续直接接入后端的 /api/dashboard 接口。

export async function fetchDashboardData(): Promise<any> {
  return Promise.resolve({
    status: 'success',
    data: {}
  })
}
