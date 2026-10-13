// Mercado IA — autor: William (https://github.com/WilliamProgramadorBR)
// Notificações da Central com decisão (12/10/2026): o botão da notificação do navegador manda a escolha para a
// página aberta (ou abre a Central na aba certa).
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', ev => ev.waitUntil(self.clients.claim()));

self.addEventListener('notificationclick', ev => {
  const n = ev.notification, dados = n.data || {};
  n.close();
  const msg = ev.action && ev.action.startsWith('op:')
    ? {tipo: 'decidir', caso: dados.caso, opcao: ev.action.slice(3)}
    : {tipo: 'abrir', aba: dados.aba, caso: dados.caso};
  ev.waitUntil((async () => {
    const lista = await self.clients.matchAll({type: 'window', includeUncontrolled: true});
    let c = lista.find(x => new URL(x.url).pathname === '/') || lista[0];
    if (!c) {
      c = await self.clients.openWindow('/?aba=' + encodeURIComponent(dados.aba || 'resumo'));
      if (!c) return;
      await new Promise(r => setTimeout(r, 2500));   // espera a página conectar
    }
    try { await c.focus(); } catch (e) { /* sem foco: tudo bem */ }
    c.postMessage(msg);
  })());
});
