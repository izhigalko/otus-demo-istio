# Практика к занятию по теме "Service mesh на примере Istio"

## Зависимости

Для выполнения задания вам потребуется установить зависимости:

- [Minikube 1.13.1](https://github.com/kubernetes/minikube/releases/tag/v1.13.1)
- [Kubectl 0.19.2](https://github.com/kubernetes/kubectl/releases/tag/v0.19.2)
- [Istioctl 1.7.3](https://github.com/istio/istio/releases/tag/1.7.3)
- [Heml 3.3.4](https://github.com/helm/helm/releases/tag/v3.3.4)

После установки нужно запустить Kubernetes. При необходимости можно изменить используемый драйвер с помощью
флага `--driver`. 

```shell script
minikube start \
--cpus=4 --memory=8g \
--cni=flannel \
--kubernetes-version="v1.19.0" \
--extra-config=apiserver.enable-admission-plugins=NamespaceLifecycle,LimitRanger,ServiceAccount,DefaultStorageClass,\
DefaultTolerationSeconds,NodeRestriction,MutatingAdmissionWebhook,ValidatingAdmissionWebhook,ResourceQuota,PodPreset \
--extra-config=apiserver.authorization-mode=Node,RBAC
```

Операции будут совершаться с помощью утилиты `kubectl`

## Содержание

* [Устройство Istio](#Устройство-Istio)
* [Ограничение доступа](#Ограничение-доступа)

## Устройство Istio

### Разворачиваем Jaeger

Jaeger - решение трассировки. Компоненты Istio, такие как: sidecar-контейнер, gateway, отправляют данные запросов в
систему. Таким образом получается полная трассировка запроса.

Добавить репозиторий в Helm:

```shell script
helm repo add jaegertracing https://jaegertracing.github.io/helm-charts
helm repo update
```

Установить оператор, разворачивающий Jaeger:

```shell script
helm install --version "2.17.0" -n jaeger-operator --create-namespace -f jaeger/operator-values.yaml \
jaeger-operator jaegertracing/jaeger-operator
``` 

Развернуть Jaeger:

```shell script
kubectl apply -f jaeger/jaeger.yaml
```

Проверить состояние Jaeger:

```shell script
kubectl get po -n jaeger -l app.kubernetes.io/instance=jaeger
```

Открыть web-интерфейс Jaeger:

```shell script
minikube service -n jaeger jaeger-query-nodeport
```

### Разворачиваем Prometheus

Prometheus - система мониторинга. С помощью неё собираются метрики Service mesh.

Добавить репозиторий в Helm:

```shell script
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add stable https://kubernetes-charts.storage.googleapis.com/
helm repo update
```

Развернуть решение по мониторингу на основе Prometheus:

```shell script
helm install --version "9.4.4" -n monitoring --create-namespace -f prometheus/operator-values.yaml prometheus \
prometheus-community/kube-prometheus-stack
``` 

Проверить состояние компонентов мониторинга:

```shell script
kubectl get po -n monitoring
```

Добавить сервис типа NodePort для прямого доступа к Prometheus и Grafana:

```shell script
kubectl apply -f prometheus/monitoring-nodeport.yaml
```

Открыть web-интерфейс Grafana:

```shell script
minikube service -n monitoring prometheus-grafana-nodeport
```

Открыть web-интерфейс Prometheus:

```shell script
minikube service -n monitoring prom-prometheus-nodeport
```

### Разворачиваем Istio 

Istio - Service mesh решение для облачных платформ, использующее Envoy.

Установить оператор, разворачивающий Istio:

```shell script
istioctl operator init --watchedNamespaces istio-system --operatorNamespace istio-operator
```

Развернуть Istio c помощью оператора:

```shell script
kubectl apply -f istio/istio.yaml
```

Проверить состояние Istio:

```shell script
kubectl get all -n istio-system -l istio.io/rev=default
```

### Устанавливаем Kiali

Kiali - доска управления Service mesh

Добавить репозиторий в Helm:

```shell script
helm repo add kiali https://kiali.org/helm-charts
helm repo update
```

Установить Kiali Operator, разворачивающий Kiali

```shell script
helm install --version "1.24.0" -n kiali-operator --create-namespace kiali-operator kiali/kiali-operator
```

Развернуть Kiali:

```shell script
kubectl apply -f kiali/kiali.yaml
```

Открыть web-интерфейс Kiali:

```shell script
minikube service -n kiali kiali-nodeport
```

### Устанавливаем echoserver

Echoserver - сервис, отдающий в виде текста параметры входящего HTTP запроса.

Развернуть приложение `echoserver` в кластере:

```shell script
kubectl apply -f app/echoserver.yaml
```

Проверить статус echoserver:

```shell script
kubectl get po -l "app=echoserver"
```

Выполнить запрос к сервису:

```shell script
curl $(minikube service echoserver --url)
```

### Устанавливаем proxy-app

Proxy-app - сервис, умеющий запрашивать другие запросы по query-параметру url. 

Собрать Docker-образ `proxy-app`:

```shell script
eval $(minikube docker-env) && docker build -t proxy-app:latest -f app/src/Dockerfile app/src
```

Развернуть приложение `proxy-app` в кластере:

```shell script
kubectl apply -f app/proxy-app.yaml
```

Проверить статус приложения:

```shell script
kubectl get po -l "app=proxy-app"
```

Выполнить запрос к сервису:

```shell script
curl $(minikube service proxy-app --url)
```

### Нагружаем приложения

Собрать нагрузочный образ:

```shell script
eval $(minikube docker-env) && docker build -t load-otus-demo:latest -f app/load/Dockerfile app/load
```

Запустить нагрузочный образ:

```shell script
kubectl apply -f app/load.yaml
```

Посмотреть логи нагрузки:

```shell script
kubectl logs -l app=load
```

## Ограничение доступа

Сервис `proxy-app` позволяет запросить другие сервисы с помощью параметра url, сделаем это.

Выполнить запрос к сервису `echoserver`:

```shell script
curl "$(minikube service proxy-app --url)?url=http://echoserver"
```

В результате исполнения команды видно, что запрос на `echoserver` проходит.

Ограничить доступ к `echoserver` для `proxy-app`:

```shell script
kubectl apply -f manage-traffic/proxy-app-sidecar-disable.yaml
```

Выполнить запрос к сервису `echoserver`:

```shell script
curl "$(minikube service proxy-app --url)?url=http://echoserver"
```

В результате исполнения команды получается ошибка, так как правила для исходящего трафика `proxy-app` настроены таким образом,
что ему запрещены любые исходящие сетевые соединения.

Открыть доступ до `echoserver`:

```shell script
kubectl apply -f manage-traffic/proxy-app-sidecar-enable.yaml
```

Выполнить запрос к сервису `echoserver`:

```shell script
curl "$(minikube service proxy-app --url)?url=http://echoserver"
```

В результате исполнения команды видно, что запрос на `echoserver` проходит.
