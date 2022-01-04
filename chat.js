const { Client, Server } = require("node-osc");

class Connection {
  constructor(io, socket) {
    this.socket = socket;
    this.io = io;

    socket.on("building", (_data) => {
      this.io.oscClient.send("/building", JSON.stringify(_data));
      socket.broadcast.emit("building", _data);
    });

    socket.on("compute eui", (_data) => {
      if (!this.io.logs)
        this.io.logs = {
          euiCalculationTriggers: 0,
        };
      this.io.logs.euiCalculationTriggers++;
      this.io.oscClient.send("/computeEui", 1);
      const clearComputeFlag = () => {
        this.io.oscClient.send("/computeEui", 0);
      };
      setTimeout(clearComputeFlag.bind(this), 10000);
      console.log("computing eui");
    });
    socket.on("disconnect", () => this.disconnect());
    socket.on("connect_error", (err) => {
      console.log(`connect_error due to ${err.message}`);
    });
  }

  disconnect() {}
}

function chat(io) {
  io.on("connection", (socket) => {
    new Connection(io, socket);
  });

  io.oscServer = new Server(3334, "0.0.0.0", () => {
    console.log("OSC Server is listening");
  });

  io.oscServer.on("/0/cost", function (msg) {
    const address = msg[0];
    const cost = msg[1];
    io.emit("cost", cost);
  });

  io.oscServer.on("/0/eui", function (msg) {
    const address = msg[0];
    const eui = msg[1];
    io.emit("eui", eui);
  });

  io.oscClient = new Client("127.0.0.1", 3333);
}

module.exports = chat;
