<script>
export default {
  data() {
    return { html: window.name };
  },
  mounted() {
    $("#out").html(window.name);
  },
};
</script>

<template>
  <div v-html="html"></div>
</template>
