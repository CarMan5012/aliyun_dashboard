import axios from 'axios'
import type { AxiosInstance, AxiosResponse } from 'axios'

const request: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

request.interceptors.request.use((config) => {
  const pwd = localStorage.getItem('aliyun_dashboard_settings_pwd')
  if (pwd) {
    config.headers['X-Settings-Password'] = pwd
  }
  return config
})

request.interceptors.response.use(
  (response: AxiosResponse) => {
    return response
  },
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export default request
