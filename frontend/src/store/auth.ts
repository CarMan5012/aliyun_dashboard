import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAuthStore = defineStore('auth', () => {
  const user = ref({
    username: 'Admin',
    role: 'Administrator',
    avatar: 'https://api.dicebear.com/7.x/bottts/svg?seed=Admin',
  })

  return {
    user,
  }
})
