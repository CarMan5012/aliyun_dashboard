import axios from 'axios'
import type { AxiosInstance, AxiosResponse } from 'axios'

const request: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
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
