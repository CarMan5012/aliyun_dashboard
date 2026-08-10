<template>
  <div class="flex h-screen bg-bgLight dark:bg-bgDark text-slate-800 dark:text-slate-200 overflow-hidden font-sans transition-colors duration-300">
    <Sidebar />
    <div class="flex-grow flex flex-col min-w-0 overflow-hidden">
      <Header />
      <main class="flex-grow p-5 lg:p-6 overflow-y-auto space-y-4">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import Sidebar from '@/components/Sidebar.vue'
import Header from '@/components/Header.vue'
</script>
