# Практика к занятию по теме "Service mesh на примере Istio"

## Зависимости

Для выполнения задания вам потребуется установить зависимости:

- [VirtualBox](https://www.virtualbox.org/wiki/Downloads)
- [Vagrant](https://www.vagrantup.com/downloads.html)

После установки нужно запустить команду запуска в корне проекта:

```shell script
vagrant up
```

Для совершения всех операций нам понадобится зайти в виртуальную машину:

```shell script
vagrant ssh
```

## Содержание

* [Устройство Istio](#Устройство-Istio)
* [Ограничение доступа](#Ограничение-доступа)
* [Конфигурация proxy](#Конфигурация-proxy)

## Устройство Istio

### Разворачиваем Istio 

На данном этапе мы установим Istio.
Так же, можно [посмотреть манифест с комментариями](istio/istio-manifest.yaml)

Применяем манифест:

```shell script
istioctl manifest apply -f istio/istio-manifest.yaml
```

Применяем настройки по-умолчанию:

```shell script
kubectl apply -f istio/defaults.yaml
```

__Стоить отметить, что все операции по изменению конфигурации Istio 
(добавление компонентов, обновление, удаление) нужно совершать с указанием манифеста,
используемого при установке.__

Дождитесь окончания установки. Далее, вы можете получить состояние
уровня управления Istio с помощью команды:

```shell script
kubectl get all -n istio-system
```

### Устанавливаем приложение

Развернем приложение в кластере:

```shell script
kubectl apply -f app/echoserver.yaml
```

Посмотреть статус приложения можно с помощью команды:

```shell script
kubectl get po -l "app=echoserver"
```

Результат данной команды вернет число контейнеров в Pod равное двум. Если посмотреть
подробнее:

```shell script
kubectl get po -l "app=echoserver" -o yaml
```

То будет видно, что в приложение был встроен sidecar-контейнер istio-proxy.
Он обеспечивает уровень данных Istio.

Echoserver доступен по ссылке:
[http://127.0.0.1:32080](http://127.0.0.1:32080)

## Ограничение доступа

### Устанавливаем приложение

Развернем другое приложение, оно будет обращаться к `echoserver`.

Для начала надо собрать образ:

```shell script
sudo docker build -t proxy-app:latest -f /home/vagrant/app/src/Dockerfile /home/vagrant/app/src/
```

Потом развернуть приложение:

```shell script
kubectl apply -f app/proxy-app.yaml
```

Посмотреть статус приложения можно с помощью команды:

```shell script
kubectl get po -l "app=proxy-app"
```

Необходимо дождаться окончания запуска приложения.

Можно посмотреть конфигурацию прокси-сервера до и после исполнения окманд с помощью:

```shell script
export POD=$(kubectl get pods --selector=app=proxy-app -o jsonpath='{.items[*].metadata.name}') && \
kubectl exec pod/$POD -c istio-proxy -- curl http://127.0.0.1:15000/config_dump | less
```

### Ограничим доступ proxy-app до echoserver

Proxy-app доступен по ссылке: 
[http://127.0.0.1:32081/?url=http://echoserver.default](http://127.0.0.1:32081/?url=http://echoserver.default)

Перейдя по ссылке выше видно, что на данный момент `echoserver` доступен для `proxy-app`.

Применим конфигурацию:
```shell script
kubectl apply -f manage-traffic/proxy-app-sidecar-disable.yaml
```

По ссылке [http://127.0.0.1:32081/?url=http://echoserver.default](http://127.0.0.1:32081/?url=http://echoserver.default)
видно, что доступ до `echoserver` пропал.

### Вернем доступ proxy-app до echoserver

Мы можем открыть доступ для `echoserver` с помощью команды:

```shell script
kubectl apply -f manage-traffic/proxy-app-sidecar-enable.yaml
```

По ссылке [http://127.0.0.1:32081/?url=http://echoserver.default](http://127.0.0.1:32081/?url=http://echoserver.default)
видно, что доступ до `echoserver` появился.

## Конфигурация proxy

Решим задачу сбора метрик с proxy добавив фильтр статистики:

```shell script
kubectl apply -f proxy-config/inbound-http-metrics.yaml
```

После этого сделаем несколько запросов к сервису:
[http://127.0.0.1:32081/?url=http://echoserver.default](http://127.0.0.1:32081/?url=http://echoserver.default).

Зайдем в [Prometheus](http://127.0.0.1:32082) и запросим данные:

```text
round(sum(rate(istio_requests_total{reporter="destination"}[1m])) by (destination_workload), 0.001)```
