def get_call(self):
        DG = nx.DiGraph()
        k8s_util = KubernetesClient(self.config)
        svcs = [svc for svc in k8s_util.get_svcs() if 'redis' not in svc and 'mongo' not in svc and 'unknown' not in svc and 'mysql' not in svc and 'rabbitmq' not in svc]
        DG.add_nodes_from(svcs)
        edges = []
        prom_sql = 'sum(istio_tcp_received_bytes_total{destination_workload_namespace=\"%s\"}) by (source_workload, destination_workload)' % self.namespace
        results = self.execute_prom(self.prom_no_range_url, prom_sql)

        prom_sql = 'sum(istio_requests_total{destination_workload_namespace=\"%s\"}) by (source_workload, destination_workload)' % self.namespace
        results = results + self.execute_prom(self.prom_no_range_url, prom_sql)

        for result in results:
            metric = result['metric']
            source = metric['source_workload']
            destination = metric['destination_workload']
            if source in svcs and destination in svcs:
                edges.append((source, destination))

        DG.add_edges_from(edges)
        return DG