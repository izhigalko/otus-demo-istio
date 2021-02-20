# Практика к занятию по теме "Service mesh на примере Istio"

## Зависимости

Для выполнения задания вам потребуется установить зависимости:

- [Minikube 1.13.1](https://github.com/kubernetes/minikube/releases/tag/v1.13.1)
- [Kubectl 0.19.2](https://github.com/kubernetes/kubectl/releases/tag/v0.19.2)
- [Istioctl 1.9.0](https://github.com/istio/istio/releases/tag/1.9.0)
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

Создать неймспейсы для операторов:

```shell script
kubectl apply -f namespaces.yaml
```

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
helm install --version "2.19.0" -n jaeger-operator -f jaeger/operator-values.yaml \
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
helm install --version "13.7.2" -n monitoring -f prometheus/operator-values.yaml prometheus \
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
helm install --version "1.29.1" -n kiali-operator kiali-operator kiali/kiali-operator
```

Развернуть Kiali:

```shell script
kubectl apply -f kiali/kiali.yaml
```

Проверить состояние Kiali:

```shell script
kubectl get po -n kiali -l app.kubernetes.io/name=kiali
```

Открыть web-интерфейс Kiali:

```shell script
minikube service -n kiali kiali-nodeport
```

### Устанавливаем echoserver

Echoserver - сервис, отдающий в виде текста параметры входящего HTTP запроса.

Собрать Docker-образ:

```shell script
eval $(minikube docker-env) && docker build -t proxy-app:latest -f app/src/Dockerfile app/src
```

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

Посмотреть логи приложения:
```shell script
kubectl logs -l app=proxy-app -c proxy-app
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

## Настраиваем взаимодействие между сервисами

Сервис `proxy-app` позволяет запросить другие сервисы с помощью параметра url, сделаем это.

Выполнить запрос к сервису `echoserver`:

```shell script
curl "$(minikube service proxy-app --url)?url=http://echoserver"
```

В результате исполнения команды видно, что запрос на `echoserver` проходит.

Ограничим доступ `proxy-app` ко всем сервисам:

```shell script
kubectl apply -f manage-traffic/proxy-app-sidecar-disable.yaml
```

Выполнить запрос к сервису `echoserver`:

```shell script
curl "$(minikube service proxy-app --url)?url=http://echoserver"
```

В результате исполнения команды получается ошибка, так как правила для исходящего трафика `proxy-app` настроены таким образом,
что ему запрещены любые исходящие сетевые соединения.

Применим настройки, в которых сказано, что `proxy-app` может осуществлять запросы к `echoserver`:

```shell script
kubectl apply -f manage-traffic/proxy-app-sidecar-enable.yaml
```

Выполнить запрос к сервису `echoserver`:

```shell script
curl "$(minikube service proxy-app --url)?url=http://echoserver"
```

В результате исполнения команды видно, что запрос на `echoserver` проходит.

## Настраиваем безопасности

В качестве примера настройки безопасности будем использовать настройку межсервисной аутентификации.

Включить аутентификацию для `echoserver`:

```shell script
kubectl apply -f auth/echoserver-auth.yaml
```

Выполнить запрос к сервису `echoserver`:

```shell script
curl "$(minikube service proxy-app --url)?url=http://echoserver"
```

Выполнить запрос к сервису с указанием токена:

```shell script
curl -H "X-AUTH-TOKEN: token" "$(minikube service proxy-app --url)?url=http://echoserver"
```

Добавить автоматическую подстановку токена при вызове сервиса `echoserver`:

```shell script
kubectl apply -f auth/proxy-app-auth.yaml
```

Выполнить запрос к сервису `echoserver` без указания токена:

```shell script
curl "$(minikube service proxy-app --url)?url=http://echoserver"
```

## Настраиваем отказоустойчивость

Рассмотрим настройку отказоустойчивости для метода `http://echoserver/error?times=3`. При его вызове
последовательно возвращается 500 ошибка в количестве, указанном в параметре `times`. В этом случае,
метод вернёт ошибку 3 раза, а на 4 вернет код 200.

```shell script
curl "$(minikube service proxy-app --url)?url=http://echoserver/error?times=3"
```

Применим правило, которое позволяет автоматически делать повтор запроса при возникновении ошибок с кодом 500
или ошибок соединения.

Применить политику повторов:

```shell script
kubectl apply -f retries/echoserver-retries.yaml
```

Выполнить запрос:

```shell script
curl "$(minikube service proxy-app --url)?url=http://echoserver/error?times=3"
```
