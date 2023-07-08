 var ws21 = null;
  var json21 = function (type, data = null) {
    return JSON.stringify({
      'type': type,
      'data': data
    })
  }
  var dd21 = function (data, error = false) {
    if (error) {
      console.error(data)
    } else {
      console.log(data)
    }
  }
  var play21 = function () {
    if (ws21) {
      console.log('连接存在')
    }
    ws21 = new WebSocket('wss://finger.cnfschool.net/')
    ws21.onopen = (res) => {
      console.log(123);
      ws21.send(json21('init'))
    }
    ws21.onclose = (res) => {
      console.error('Close', res)
      ws21 = null
    }
    ws21.onerror = (res) => {
      console.error('Error', res)
      ws21 = null
    }
    ws21.onmessage = (res) => {
      res = JSON.parse(res.data)
      let type = res.type
      let data = res.data
      switch (res.type) {
        case 'init':
          dd21('【请输入】：mj("你的昵称")，并回车，注意括号需要使用英文括号')
          break
        case 'win':
          dd21(data,true)
          break;
        case 'deal':
          dd21('-'.repeat(100) + '\r\n\r\n' + data + '\r\n' + '-'.repeat(100))
          break
        case 'broadcast':
          dd21('【广播】：' + data)
          break
        case 'tip':
          dd21('【Tip】：' + data)
          break
        case 'now':
          dd21('【当前状态】：' + data)
          break
        case 'name':
          dd21('【接到一条信息】：' + data)
          dd21('如果你准备好了就输入，ready()')
          break
        case 'master':
          dd21('【叫庄】：请输入：master() 抢庄，30秒后自动分配AI')
          break
        case 'money':
          dd21('【加注】：加注请输入：money(100)，不加注请输入：pass()，弃牌：bad()，30秒之后自动pass')
          break
        case 'want':
          dd21('【叫牌】：叫牌请输入：want()，不叫牌请输入：pass()，弃牌：bad()，等待开牌：show()，30秒之后自动pass')
          break
        case 'hand':
          dd21('【手牌】：' + data.join('，'))
          break
        case 'nomoney':
          dd21('Gei Gei 你钱都没有了还玩个锤子', true)
          break
      }
    }

  }
  var help = function () {
    dd21(`
      游戏规则非常easy
      每个命令输入完成后请敲击回车
      如果你准备好了就输入： ready()
      发送嘲讽消息： msg("嘲讽")
      改名： mj("你的名字")
      叫庄： master()
      加注： money(100)
      查看当前状态： now()
      查看手牌： hand()
      要牌:  want()
      不要牌： pass()
      弃牌，放弃本局： bad()
    `)
  }
  var ready = function () {
    ws21.send(json21('ready'))
  }
  var master = function () {
    ws21.send(json21('master'))
  }
  var money = function (number) {
    number = parseInt(number)
    ws21.send(json21('money', number))
  }
  var mj = function (str) {
    ws21.send(json21('name', str))
  }
  var pass = function () {
    ws21.send(json21('pass'))
  }
  var show = function () {
    ws21.send(json21('show'))
  }
  var want = function () {
    ws21.send(json21('want'))
  }
  var msg = function (msg) {
    ws21.send(json21('broadcast', msg))
  }
  var bad = function (msg) {
    ws21.send(json21('bad'))
  }
