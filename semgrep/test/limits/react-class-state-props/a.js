const tainted = document.location.search;

export class Stateful extends React.Component {
  constructor() {
    this.state = { value: tainted };
  }
  show() {
    $("#out").html(this.state.value);
  }
}

export class WithProps extends React.Component {
  show() {
    $("#out").html(this.props.value);
  }
}
WithProps.defaultProps = { value: tainted };
